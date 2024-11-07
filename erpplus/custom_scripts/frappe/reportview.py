import frappe
from frappe.desk.reportview import get_form_params, compress
from frappe.model.db_query import DatabaseQuery
from frappe.model.utils import is_virtual_doctype
from frappe.model.base_document import get_controller
from frappe.utils import (
	cstr,
	flt,
	get_filter,
	get_time
)
from frappe.model.db_query import (
	cast_name, 
	get_additional_filter_field,
	get_date_range,
	get_between_date_filter
)
from frappe.database.utils import FallBackDateTimeStr, NestedSetHierarchy
import datetime
from frappe.query_builder.utils import Column

@frappe.whitelist()
@frappe.read_only()
def get():
	args = get_form_params()
	# If virtual doctype get data from controller het_list method
	if is_virtual_doctype(args.doctype):
		controller = get_controller(args.doctype)
		data = compress(controller.get_list(args))
	else:
		data = compress(execute(**args), args=args)
	return data

def execute(doctype, *args, **kwargs):
	return CustomDatabaseQuery(doctype).execute(*args, **kwargs)

class CustomDatabaseQuery(DatabaseQuery):
	def prepare_filter_condition(self, f):
		"""Returns a filter condition in the format:
		ifnull(`tabDocType`.`fieldname`, fallback) operator "value"
		"""

		# TODO: refactor

		from frappe.boot import get_additional_filters_from_hooks

		additional_filters_config = get_additional_filters_from_hooks()
		f = get_filter(self.doctype, f, additional_filters_config)

		tname = "`tab" + f.doctype + "`"
		if tname not in self.tables:
			self.append_table(tname)

		column_name = cast_name(f.fieldname if "ifnull(" in f.fieldname else f"{tname}.`{f.fieldname}`")

		if f.operator.lower() in additional_filters_config:
			f.update(get_additional_filter_field(additional_filters_config, f, f.value))

		meta = frappe.get_meta(f.doctype)

		# primary key is never nullable, modified is usually indexed by default and always present
		can_be_null = f.fieldname not in ("name", "modified", "creation")

		# prepare in condition
		if f.operator.lower() in NestedSetHierarchy:
			values = f.value or ""

			# TODO: handle list and tuple
			# if not isinstance(values, (list, tuple)):
			# 	values = values.split(",")
			field = meta.get_field(f.fieldname)
			ref_doctype = field.options if field else f.doctype
			lft, rgt = "", ""
			if f.value:
				lft, rgt = frappe.db.get_value(ref_doctype, f.value, ["lft", "rgt"]) or (0, 0)

			# Get descendants elements of a DocType with a tree structure
			if f.operator.lower() in ("descendants of", "not descendants of"):
				result = frappe.get_all(
					ref_doctype, filters={"lft": [">", lft], "rgt": ["<", rgt]}, order_by="`lft` ASC"
				)
			else:
				# Get ancestor elements of a DocType with a tree structure
				result = frappe.get_all(
					ref_doctype, filters={"lft": ["<", lft], "rgt": [">", rgt]}, order_by="`lft` DESC"
				)

			fallback = "''"
			value = [frappe.db.escape((cstr(v.name) or "").strip(), percent=False) for v in result]
			if len(value):
				value = f"({', '.join(value)})"
			else:
				value = "('')"

			# changing operator to IN as the above code fetches all the parent / child values and convert into tuple
			# which can be directly used with IN operator to query.
			f.operator = (
				"not in" if f.operator.lower() in ("not ancestors of", "not descendants of") else "in"
			)

		elif f.operator.lower() in ("in", "not in"):
			# if values contain '' or falsy values then only coalesce column
			# for `in` query this is only required if values contain '' or values are empty.
			# for `not in` queries we can't be sure as column values might contain null.
			if f.operator.lower() == "in":
				can_be_null &= not f.value or any(v is None or v == "" for v in f.value)

			values = f.value or ""
			if isinstance(values, str):
				values = values.split(",")

			fallback = "''"
			value = [frappe.db.escape((cstr(v) or "").strip(), percent=False) for v in values]
			if len(value):
				value = f"({', '.join(value)})"
			else:
				value = "('')"

		else:
			escape = True
			df = meta.get("fields", {"fieldname": f.fieldname})
			df = df[0] if df else None

			if df and df.fieldtype in ("Check", "Float", "Int", "Currency", "Percent"):
				can_be_null = False

			if f.operator.lower() in ("previous", "next", "timespan"):
				date_range = get_date_range(f.operator.lower(), f.value)
				f.operator = "between"
				f.value = date_range
				fallback = f"'{FallBackDateTimeStr}'"

			if f.operator.lower() in (">", ">=") and (
				f.fieldname in ("creation", "modified")
				or (df and (df.fieldtype == "Date" or df.fieldtype == "Datetime"))
			):
				# Null values can never be greater than any non-null value
				can_be_null = False

			if f.operator in (">", "<", ">=", "<=") and (f.fieldname in ("creation", "modified")):
				value = cstr(f.value)
				can_be_null = False
				fallback = f"'{FallBackDateTimeStr}'"

			elif f.operator.lower() in ("between") and (
				f.fieldname in ("creation", "modified")
				or (df and (df.fieldtype == "Date" or df.fieldtype == "Datetime"))
			):
				escape = False
				# Between operator never needs to check for null
				# Explanation: Consider SQL -> `COLUMN between X and Y`
				# Actual computation:
				#     for row in rows:
				#     if Y > row.COLUMN > X:
				#         yield row

				# Since Y and X can't be null, null value in column will never match filter, so
				# coalesce is extra cost that prevents index usage
				can_be_null = False

				value = get_between_date_filter(f.value, df)
				fallback = f"'{FallBackDateTimeStr}'"

			elif f.operator.lower() == "is":
				if f.value == "set":
					f.operator = "!="
					# Value can technically be null, but comparing with null will always be falsy
					# Not using coalesce here is faster because indexes can be used.
					# null != '' -> null ~ falsy
					# '' != '' -> false
					can_be_null = False
				elif f.value == "not set":
					f.operator = "="
					fallback = "''"
					can_be_null = True

				value = ""

				if can_be_null and "ifnull" not in column_name.lower():
					column_name = f"ifnull({column_name}, {fallback})"

			elif df and df.fieldtype == "Date":
				value = frappe.db.format_date(f.value)
				fallback = "'0001-01-01'"

			elif (df and df.fieldtype == "Datetime") or isinstance(f.value, datetime.datetime):
				value = frappe.db.format_datetime(f.value)
				fallback = f"'{FallBackDateTimeStr}'"

			elif df and df.fieldtype == "Time":
				value = get_time(f.value).strftime("%H:%M:%S.%f")
				fallback = "'00:00:00'"

			elif f.operator.lower() in ("like", "not like") or (
				isinstance(f.value, str)
				and (not df or df.fieldtype not in ["Float", "Int", "Currency", "Percent", "Check"])
			):
				value = "" if f.value is None else f.value
				fallback = "''"

				if f.operator.lower() in ("like", "not like") and isinstance(value, str):
					# because "like" uses backslash (\) for escaping
					value = value.replace("\\", "\\\\").replace("%", "%%")

			elif f.operator == "=" and df and df.fieldtype in ["Link", "Data"]:  # TODO: Refactor if possible
				value = f.value or "''"
				fallback = "''"

			elif f.fieldname == "name":
				value = f.value or "''"
				fallback = "''"

			else:
				value = flt(f.value)
				fallback = 0

			if isinstance(f.value, Column):
				can_be_null = False  # added to avoid the ifnull/coalesce addition
				quote = '"' if frappe.conf.db_type == "postgres" else "`"
				value = f"{tname}.{quote}{f.value.name}{quote}"

			# escape value
			elif escape and isinstance(value, str):
				value = f"{frappe.db.escape(value, percent=False)}"

		if (
			self.ignore_ifnull
			or not can_be_null
			or (f.value and f.operator.lower() in ("=", "like"))
			or "ifnull(" in column_name.lower()
		):
			if f.operator.lower() == "like" and frappe.conf.get("db_type") == "postgres":
				f.operator = "ilike"
			
			# Customization: If it's the doctype is item and the fieldname is 
			# description, then break it down to individual words to search
			if f.operator.lower() == "like" and column_name == "`tabItem`.`description`" \
				and len(value.split(" ")) > 1:

				value = value.replace("%", "").replace("'", "")
				words = value.split(" ")
				if len(words) > 5:
					words = words[:5]
				condition = "(" + " AND ".join([f"{column_name} {f.operator} '%%{word}%%'" for word in words]) + ")"
			else:
				condition = f"{column_name} {f.operator} {value}"
		else:
			condition = f"ifnull({column_name}, {fallback}) {f.operator} {value}"

		return condition