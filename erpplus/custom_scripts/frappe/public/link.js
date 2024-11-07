// special features for link
// buttons
// autocomplete
// link validation
// custom queries
// add_fetches
import Awesomplete from "awesomplete";

frappe.ui.form.recent_link_validations = {};

frappe.ui.form.ControlLink = class ControlLink extends frappe.ui.form.ControlLink {
	static trigger_change_on_input_event = false;
	setup_awesomeplete() {
		let me = this;

		this.$input.cache = {};

		this.awesomplete = new Awesomplete(me.input, {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
			replace: function (item) {
				// Override Awesomeplete replace function as it is used to set the input value
				// https://github.com/LeaVerou/awesomplete/issues/17104#issuecomment-359185403
				this.input.value = me.get_translated(item.label || item.value);
			},
			data: function (item) {
				return {
					label: me.get_translated(item.label || item.value),
					value: item.value,
				};
			},
			filter: function () {
				return true;
			},
			item: function (item) {
				let d = this.get_item(item.value);
				if (!d.label) {
					d.label = d.value;
				}

				let _label = me.get_translated(d.label);
				let html = d.html || "<strong>" + _label + "</strong>";
				if (
					d.description &&
					// for title links, we want to inlude the value in the description
					// because it will not visible otherwise
					(me.is_title_link() || d.value !== d.description)
				) {
					html += '<br><span class="small">' + __(d.description) + "</span>";
				}
				return $("<li></li>")
					.data("item.autocomplete", d)
					.prop("aria-selected", "false")
					.html(`<a><p title="${frappe.utils.escape_html(_label)}">${html}</p></a>`)
					.get(0);
			},
			sort: function () {
				return 0;
			},
		});

		this.custom_awesomplete_filter && this.custom_awesomplete_filter(this.awesomplete);

		this.$input.on(
			"input",
			frappe.utils.debounce(function (e) {
				var doctype = me.get_options();
				if (!doctype) return;
				if (!me.$input.cache[doctype]) {
					me.$input.cache[doctype] = {};
				}

				var term = e.target.value;

				if (me.$input.cache[doctype][term] != null) {
					// immediately show from cache
					me.awesomplete.list = me.$input.cache[doctype][term];
				}
				var args = {
					txt: term,
					doctype: doctype,
					ignore_user_permissions: me.df.ignore_user_permissions,
					reference_doctype: me.get_reference_doctype() || "",
				};

				me.set_custom_query(args);

				// Customization: Change the item search query to our custom one
				if(args.query && args.query == "erpnext.controllers.queries.item_query") {
					args.query = "erpplus.custom_scripts.queries.item_query";
				}

				frappe.call({
					type: "POST",
					method: "frappe.desk.search.search_link",
					no_spinner: true,
					args: args,
					callback: function (r) {
						if (!window.Cypress && !me.$input.is(":focus")) {
							return;
						}
						r.results = me.merge_duplicates(r.results);

						// show filter description in awesomplete
						if (args.filters) {
							let filter_string = me.get_filter_description(args.filters);
							if (filter_string) {
								r.results.push({
									html: `<span class="text-muted" style="line-height: 1.5">${filter_string}</span>`,
									value: "",
									action: () => {},
								});
							}
						}

						if (!me.df.only_select) {
							if (frappe.model.can_create(doctype)) {
								// new item
								r.results.push({
									html:
										"<span class='text-primary link-option'>" +
										"<i class='fa fa-plus' style='margin-right: 5px;'></i> " +
										__("Create a new {0}", [__(me.get_options())]) +
										"</span>",
									label: __("Create a new {0}", [__(me.get_options())]),
									value: "create_new__link_option",
									action: me.new_doc,
								});
							}

							//custom link actions
							let custom__link_options =
								frappe.ui.form.ControlLink.link_options &&
								frappe.ui.form.ControlLink.link_options(me);

							if (custom__link_options) {
								r.results = r.results.concat(custom__link_options);
							}

							// advanced search
							if (locals && locals["DocType"]) {
								// not applicable in web forms
								r.results.push({
									html:
										"<span class='text-primary link-option'>" +
										"<i class='fa fa-search' style='margin-right: 5px;'></i> " +
										__("Advanced Search") +
										"</span>",
									label: __("Advanced Search"),
									value: "advanced_search__link_option",
									action: me.open_advanced_search,
								});
							}
						}
						me.$input.cache[doctype][term] = r.results;
						me.awesomplete.list = me.$input.cache[doctype][term];
						me.toggle_href(doctype);
					},
				});
			}, 500)
		);

		this.$input.on("blur", function () {
			if (me.selected) {
				me.selected = false;
				return;
			}
			let value = me.get_input_value();
			let label = me.get_label_value();
			let last_value = me.last_value || "";
			let last_label = me.label || "";

			if (value !== last_value) {
				me.parse_validate_and_set_in_model(value, null, label);
			}
		});

		this.$input.on("awesomplete-open", () => {
			this.autocomplete_open = true;

			if (!me.get_label_value()) {
				// hide link arrow to doctype if none is set
				me.$link.toggle(false);
			}
		});

		this.$input.on("awesomplete-close", (e) => {
			this.autocomplete_open = false;

			if (!me.get_label_value()) {
				// hide link arrow to doctype if none is set
				me.$link.toggle(false);
			}
		});

		this.$input.on("awesomplete-select", function (e) {
			var o = e.originalEvent;
			var item = me.awesomplete.get_item(o.text.value);

			me.autocomplete_open = false;

			// prevent selection on tab
			let TABKEY = 9;
			if (e.keyCode === TABKEY) {
				e.preventDefault();
				me.awesomplete.close();
				return false;
			}

			if (item.action) {
				item.value = "";
				item.label = "";
				item.action.apply(me);
			}

			// if remember_last_selected is checked in the doctype against the field,
			// then add this value
			// to defaults so you do not need to set it again
			// unless it is changed.
			if (me.df.remember_last_selected_value) {
				frappe.boot.user.last_selected_values[me.df.options] = item.value;
			}

			me.parse_validate_and_set_in_model(item.value, null, item.label);
		});

		this.$input.on("awesomplete-selectcomplete", function (e) {
			let o = e.originalEvent;
			if (o.text.value.indexOf("__link_option") !== -1) {
				me.$input.val("");
			}
		});
	}
};

if (Awesomplete) {
	Awesomplete.prototype.get_item = function (value) {
		return this._list.find(function (item) {
			return item.value === value;
		});
	};
}
