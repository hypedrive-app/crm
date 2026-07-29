# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class CRMPlivoSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auth_id: DF.Data | None
		auth_token: DF.Password | None
		enabled: DF.Check
		record_call: DF.Check
		webhook_verify_token: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.verify_credentials()

	def verify_credentials(self):
		if self.enabled:
			response = requests.get(
				f"https://api.plivo.com/v1/Account/{self.auth_id}/",
				auth=(self.auth_id, self.get_password("auth_token")),
			)
			if response.status_code != 200:
				frappe.throw(
					_("Please enter a valid Plivo Auth ID & Auth Token: {0}").format(response.reason),
					title=_("Invalid credentials"),
				)
