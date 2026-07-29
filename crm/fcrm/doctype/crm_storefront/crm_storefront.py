# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CRMStorefront(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		organization: DF.Link
		platform: DF.Link
		store_url: DF.SmallText | None
	# end: auto-generated types

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Organization",
				"type": "Link",
				"key": "organization",
				"options": "CRM Organization",
				"width": "16rem",
			},
			{
				"label": "Platform",
				"type": "Link",
				"key": "platform",
				"options": "CRM Platform",
				"width": "10rem",
			},
			{
				"label": "Store URL",
				"type": "Data",
				"key": "store_url",
				"width": "18rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"organization",
			"organization_logo",
			"platform",
			"store_url",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	def parse_list_data(storefronts):
		if not storefronts:
			return []
		organizations = {s.get("organization") for s in storefronts if s.get("organization")}
		logos = {}
		if organizations:
			logos = {
				row.name: row.organization_logo
				for row in frappe.get_all(
					"CRM Organization",
					filters={"name": ["in", list(organizations)]},
					fields=["name", "organization_logo"],
				)
			}
		for storefront in storefronts:
			storefront["organization_logo"] = logos.get(storefront.get("organization"))
		return storefronts
