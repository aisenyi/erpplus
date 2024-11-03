frappe.link_search = function (doctype, args, callback, btn) {
	if (!args) {
		args = {
			txt: "",
		};
	}
	args.doctype = doctype;
	if (!args.searchfield) {
		args.searchfield = "name";
	}

	// Customization: Change the item search query to our custom one
	if (args.query && args.query == "erpnext.controllers.queries.item_query") {
		args.query = "erpplus.custom_scripts.queries.item_query";
	}

	frappe.call({
		method: "frappe.desk.search.search_widget",
		type: "POST",
		args: args,
		callback: function (r) {
			callback && callback(r);
		},
		btn: btn,
	});
};