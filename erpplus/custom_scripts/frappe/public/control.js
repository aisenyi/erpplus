import "../../../../../frappe/frappe/public/js/frappe/form/controls/base_control";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/base_input";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/data";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/int";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/float";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/currency";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/date";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/time";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/datetime";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/date_range";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/select";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/link";
import "./link";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/dynamic_link";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/text";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/code";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/text_editor";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/comment";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/check";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/image";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/attach";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/attach_image";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/table";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/color";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/signature";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/password";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/button";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/html";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/markdown_editor";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/html_editor";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/heading";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/autocomplete";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/barcode";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/geolocation";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/multiselect";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/multicheck";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/table_multiselect";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/multiselect_pills";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/multiselect_list";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/rating";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/duration";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/icon";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/phone";
import "../../../../../frappe/frappe/public/js/frappe/form/controls/json";

frappe.ui.form.make_control = function (opts) {
	var control_class_name = "Control" + opts.df.fieldtype.replace(/ /g, "");
	if (frappe.ui.form[control_class_name]) {
		return new frappe.ui.form[control_class_name](opts);
	} else {
		// eslint-disable-next-line
		console.log("Invalid Control Name: " + opts.df.fieldtype);
	}
};
