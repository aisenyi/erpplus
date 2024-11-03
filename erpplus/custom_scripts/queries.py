import frappe
import json
from frappe import scrub, _
from frappe.utils import nowdate
from frappe.desk.reportview import get_filters_cond, get_match_cond

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	doctype = "Item"
	conditions = []

	if isinstance(filters, str):
		filters = json.loads(filters)

	# Get searchfields from meta and use in Item Link field query
	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()

	columns = ""
	extra_searchfields = [field for field in searchfields if field not in ["name", "description"]]

	if extra_searchfields:
		columns += ", " + ", ".join(extra_searchfields)

	if "description" in searchfields:
		columns += """, if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as description"""

	searchfields = searchfields + [
		field
		for field in [searchfield or "name", "item_code", "item_group", "item_name"]
		if field not in searchfields
	]

	# Customization: Break down the sentence into words and search for each word
	# but only if the search text is less than five words
	wordparams = {}
	if len(txt.split()) < 5 and len(txt.split()) > 1:
		words = txt.split()
		oldsearch = searchfields
		searchfields = ""
		for i in range(len(words)):
			searchfields += ") and (" if i > 0 else "("
			searchfields += " or ".join([field + " like %(word" + str(i) + ")s" for field in oldsearch])
			wordparams[f"word{i}"] = f"%{words[i]}%"
		searchfields += ")"
	else:
		searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	if filters and isinstance(filters, dict):
		if filters.get("customer") or filters.get("supplier"):
			party = filters.get("customer") or filters.get("supplier")
			item_rules_list = frappe.get_all(
				"Party Specific Item",
				filters={"party": party},
				fields=["restrict_based_on", "based_on_value"],
			)

			filters_dict = {}
			for rule in item_rules_list:
				if rule["restrict_based_on"] == "Item":
					rule["restrict_based_on"] = "name"
				filters_dict[rule.restrict_based_on] = []

			for rule in item_rules_list:
				filters_dict[rule.restrict_based_on].append(rule.based_on_value)

			for filter in filters_dict:
				filters[scrub(filter)] = ["in", filters_dict[filter]]

			if filters.get("customer"):
				del filters["customer"]
			else:
				del filters["supplier"]
		else:
			filters.pop("customer", None)
			filters.pop("supplier", None)

	description_cond = ""
	if frappe.db.count(doctype, cache=True) < 50000:
		# scan description only if items are less than 50000
		description_cond = "or tabItem.description LIKE %(txt)s"

	# Customization: Add the individual word parameters to the default paramaters
	allparams = {
			"today": nowdate(),
			"txt": "%%%s%%" % txt,
			"_txt": txt.replace("%", ""),
			"start": start,
			"page_len": page_len,
		}
	allparams.update(wordparams)

	return frappe.db.sql(
		"""select
			tabItem.name {columns}
		from tabItem
		where tabItem.docstatus < 2
			and tabItem.disabled=0
			and tabItem.has_variants=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and ({scond} or tabItem.item_code IN (select parent from `tabItem Barcode` where barcode LIKE %(txt)s)
				{description_cond})
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(
			columns=columns,
			scond=searchfields,
			fcond=get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
			mcond=get_match_cond(doctype).replace("%", "%%"),
			description_cond=description_cond,
		),
		allparams,
		as_dict=as_dict,
	)