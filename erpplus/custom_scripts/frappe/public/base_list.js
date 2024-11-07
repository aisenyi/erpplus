frappe.provide("frappe.views");

frappe.views.BaseList = class BaseList extends frappe.views.BaseList{
	refresh() {
		let args = this.get_call_args();
		if (this.no_change(args)) {
			// console.log('throttled');
			return Promise.resolve();
		}
		this.freeze(true);

		// Customization: If if it's item doctype, change the search mthod.
		// This is for enabling description searching in any direction
		if(args.args.doctype == "Item"){
			args.method = "erpplus.custom_scripts.frappe.reportview.get";
		}

		// fetch data from server
		return frappe.call(args).then((r) => {
			// render
			this.prepare_data(r);
			this.toggle_result_area();
			this.before_render();
			this.render();
			this.after_render();
			this.freeze(false);
			this.reset_defaults();
			if (this.settings.refresh) {
				this.settings.refresh(this);
			}
		});
	}
};