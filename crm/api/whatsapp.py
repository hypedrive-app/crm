import json
import re

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property

from crm.api.doc import get_assigned_users
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.integrations.api import get_contact_lead_or_deal_from_number

ALLOWED_WHATSAPP_ROLES = ["System Manager", "Sales Manager", "Sales User"]


def validate_access(reference_doctype=None, reference_name=None, permtype="read"):
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if reference_doctype and reference_name:
		if not frappe.db.exists(reference_doctype, reference_name):
			frappe.throw(
				_("Reference document {0} {1} does not exist.").format(reference_doctype, reference_name),
				frappe.DoesNotExistError,
			)
		reference_doc = frappe.get_doc(reference_doctype, reference_name)
		if not reference_doc.has_permission(permtype):
			frappe.throw(
				_("Not permitted to access reference document {0} {1}.").format(
					reference_doctype, reference_name
				),
				frappe.PermissionError,
			)
		return reference_doc

	return None


def validate(doc, method):
	phone_number = doc.get("from") if doc.type == "Incoming" else doc.get("to")
	if phone_number:
		try:
			name, doctype = get_contact_lead_or_deal_from_number(phone_number)
			if doctype and name is not None:
				doc.reference_doctype = doctype
				doc.reference_name = name
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM WhatsApp: failed to resolve contact from number")


def on_update(doc, method):
	frappe.publish_realtime(
		"whatsapp_message",
		{
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
		},
	)

	notify_agent(doc)


def notify_agent(doc):
	if doc.type == "Incoming":
		if not doc.reference_doctype or not doc.reference_name:
			return
		doctype = doc.reference_doctype
		if doctype and doctype.startswith("CRM "):
			doctype = doctype[4:].lower()
		safe_reference_name = frappe.utils.escape_html(doc.reference_name)
		notification_text = f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{_("You")}</span>
                <span>{_("received a whatsapp message in {0}").format(doctype)}</span>
                <span class="font-medium text-ink-gray-9">{safe_reference_name}</span>
            </div>
        """
		assigned_users = get_assigned_users(doc.reference_doctype, doc.reference_name)
		for user in assigned_users:
			notify_user(
				{
					"owner": doc.owner,
					"assigned_to": user,
					"notification_type": "WhatsApp",
					"message": doc.message,
					"notification_text": notification_text,
					"reference_doctype": "WhatsApp Message",
					"reference_docname": doc.name,
					"redirect_to_doctype": doc.reference_doctype,
					"redirect_to_docname": doc.reference_name,
				}
			)


@frappe.whitelist()
def is_whatsapp_enabled():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	default_outgoing = frappe.get_cached_value(
		"WhatsApp Settings", "WhatsApp Settings", "default_outgoing_account"
	)
	if not default_outgoing:
		return False
	status = frappe.get_cached_value("WhatsApp Account", default_outgoing, "status")
	return status == "Active"


@frappe.whitelist()
def is_whatsapp_installed():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	return True


@frappe.whitelist()
def get_whatsapp_messages(reference_doctype: str, reference_name: str):
	reference_doc = validate_access(reference_doctype, reference_name)
	# twilio integration app is not compatible with crm app
	# crm has its own twilio integration in built
	if "twilio_integration" in frappe.get_installed_apps():
		return []
	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []
	messages = []

	if reference_doctype == "CRM Deal":
		lead = reference_doc.get("lead")
		if lead:
			validate_access("CRM Lead", lead)
			messages = frappe.get_all(
				"WhatsApp Message",
				filters={
					"reference_doctype": "CRM Lead",
					"reference_name": lead,
				},
				fields=[
					"name",
					"type",
					"to",
					"from",
					"content_type",
					"message_type",
					"attach",
					"template",
					"use_template",
					"message_id",
					"is_reply",
					"reply_to_message_id",
					"creation",
					"message",
					"status",
					"reference_doctype",
					"reference_name",
					"template_parameters",
					"template_header_parameters",
					"buttons",
					"flow",
					"flow_cta",
					"flow_response",
				],
			)

	messages += frappe.get_all(
		"WhatsApp Message",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		fields=[
			"name",
			"type",
			"to",
			"from",
			"content_type",
			"message_type",
			"attach",
			"template",
			"use_template",
			"message_id",
			"is_reply",
			"reply_to_message_id",
			"creation",
			"message",
			"status",
			"reference_doctype",
			"reference_name",
			"template_parameters",
			"template_header_parameters",
			"buttons",
			"flow",
			"flow_cta",
			"flow_response",
		],
	)

	# Filter messages to get only Template messages
	template_messages = [message for message in messages if message["message_type"] == "Template"]

	# Iterate through template messages
	for template_message in template_messages:
		# Find the template that this message is using
		if not frappe.db.exists("WhatsApp Templates", template_message["template"]):
			continue
		template = frappe.get_doc("WhatsApp Templates", template_message["template"])

		if template:
			template_message["template_name"] = template.template_name
			if template_message["template_parameters"]:
				parameters = json.loads(template_message["template_parameters"])
				template.template = parse_template_parameters(template.template, parameters)

			template_message["template"] = template.template
			if template_message["template_header_parameters"]:
				header_parameters = json.loads(template_message["template_header_parameters"])
				template.header = parse_template_parameters(template.header, header_parameters)
			template_message["header"] = template.header
			template_message["footer"] = template.footer

	# Filter messages to get only flow messages (both the outgoing "here's a
	# form" message and the incoming filled-out response carry content_type
	# 'flow'; only the outgoing one has a `flow` link to resolve a display name)
	flow_messages = [message for message in messages if message["content_type"] == "flow" and message.get("flow")]
	for flow_message in flow_messages:
		if not frappe.db.exists("WhatsApp Flow", flow_message["flow"]):
			continue
		flow_message["flow_name"] = frappe.get_cached_value("WhatsApp Flow", flow_message["flow"], "flow_name")

	# Incoming flow responses carry raw JSON answers; parse them here so the
	# frontend renders a readable summary instead of a raw JSON blob.
	for message in messages:
		if message["content_type"] == "flow" and message.get("flow_response"):
			try:
				message["flow_response"] = (
					json.loads(message["flow_response"])
					if isinstance(message["flow_response"], str)
					else message["flow_response"]
				)
			except (TypeError, ValueError):
				message["flow_response"] = None

	# Filter messages to get only reaction messages
	reaction_messages = [message for message in messages if message["content_type"] == "reaction"]
	reaction_messages.reverse()

	# Iterate through reaction messages
	for reaction_message in reaction_messages:
		# Find the message that this reaction is reacting to
		reacted_message = next(
			(m for m in messages if m["message_id"] == reaction_message["reply_to_message_id"]),
			None,
		)

		# If the reacted message is found, add the reaction to it
		if reacted_message:
			reacted_message["reaction"] = reaction_message["message"]

	for message in messages:
		from_name = get_from_name(message) if message["from"] else _("You")
		message["from_name"] = from_name
	# Filter messages to get only replies
	reply_messages = [message for message in messages if message["is_reply"]]

	# Iterate through reply messages
	for reply_message in reply_messages:
		# Find the message that this message is replying to
		replied_message = next(
			(m for m in messages if m["message_id"] == reply_message["reply_to_message_id"]),
			None,
		)

		# If the replied message is found, add the reply details to the reply message
		if replied_message:
			from_name = get_from_name(reply_message) if replied_message["from"] else _("You")
			message = replied_message["message"]
			if replied_message["message_type"] == "Template":
				message = replied_message["template"]
			reply_message["reply_message"] = message
			reply_message["header"] = replied_message.get("header") or ""
			reply_message["footer"] = replied_message.get("footer") or ""
			reply_message["reply_to"] = replied_message["name"]
			reply_message["reply_to_type"] = replied_message["type"]
			reply_message["reply_to_from"] = from_name

	return [message for message in messages if message["content_type"] != "reaction"]


@frappe.whitelist()
def create_whatsapp_message(
	reference_doctype: str,
	reference_name: str,
	message: str,
	to: str,
	attach: str,
	reply_to: str,
	content_type: str = "text",
):
	validate_access(reference_doctype, reference_name)
	doc = frappe.new_doc("WhatsApp Message")

	if reply_to:
		if not frappe.db.exists("WhatsApp Message", reply_to):
			frappe.throw(_("Referenced WhatsApp message does not exist."), frappe.DoesNotExistError)
		reply_doc = frappe.get_doc("WhatsApp Message", reply_to)
		if not reply_doc.has_permission("read"):
			frappe.throw(
				_("Not permitted to access the referenced WhatsApp message."), frappe.PermissionError
			)
		validate_access(reply_doc.reference_doctype, reply_doc.reference_name)
		doc.update(
			{
				"is_reply": True,
				"reply_to_message_id": reply_doc.message_id,
			}
		)

	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message": message or attach,
			"to": to,
			"attach": attach,
			"content_type": content_type,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def send_whatsapp_template(
	reference_doctype: str,
	reference_name: str,
	template: str,
	to: str,
	body_parameters: list | str | None = None,
	header_parameters: list | str | None = None,
):
	validate_access(reference_doctype, reference_name)

	if not frappe.db.exists("WhatsApp Templates", template):
		frappe.throw(_("WhatsApp Template {0} does not exist.").format(template), frappe.DoesNotExistError)

	if isinstance(body_parameters, str):
		body_parameters = json.loads(body_parameters) if body_parameters else []
	if isinstance(header_parameters, str):
		header_parameters = json.loads(header_parameters) if header_parameters else []
	body_parameters = body_parameters or []
	header_parameters = header_parameters or []

	template_doc = frappe.get_doc("WhatsApp Templates", template)
	expected_body_params = _count_template_placeholders(template_doc.template)
	if len(body_parameters) < expected_body_params or any(not p for p in body_parameters):
		frappe.throw(
			_(
				"This template expects {0} body parameter(s), but {1} were provided. "
				"Please fill in all template parameters before sending."
			).format(expected_body_params, len(body_parameters))
		)

	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message_type": "Template",
			"message": "Template message",
			"content_type": "text",
			"use_template": True,
			"template": template,
			"to": to,
		}
	)
	if body_parameters:
		# frappe_whatsapp's send_template() reads body_param as a JSON object
		# and iterates its .values() in insertion order, so a numeric-keyed
		# dict preserves {{1}}, {{2}}, ... ordering.
		doc.body_param = json.dumps({str(i + 1): value for i, value in enumerate(body_parameters)})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def send_whatsapp_interactive(
	reference_doctype: str,
	reference_name: str,
	to: str,
	message: str,
	interactive_type: str,
	buttons: list | str | None = None,
	list_button_label: str | None = None,
	sections: list | str | None = None,
	reply_to: str | None = None,
):
	"""Send a WhatsApp interactive message: quick-reply buttons or a list menu.

	`interactive_type` is "button" or "list":
	- "button": `buttons` is a list of up to 3 {"id", "title"} dicts.
	- "list": `sections` is a list of up to 10 {"title", "rows": [{"id",
	  "title", "description"?}, ...]} dicts (up to 10 rows total across all
	  sections, matching Meta's own list-message ceiling), and
	  `list_button_label` is the label shown on the menu-opening button
	  (defaults to "Select Option" if omitted).

	Builds the rich dict shape frappe_whatsapp's WhatsAppMessage.send_outgoing
	understands for content_type "interactive" (see whatsapp_message.py) and
	stores it on the doc's `buttons` JSON field verbatim; frappe_whatsapp does
	the actual Meta Graph API payload construction on send.
	"""
	validate_access(reference_doctype, reference_name)

	if interactive_type not in ("button", "list"):
		frappe.throw(_("Interactive type must be 'button' or 'list'."))

	if not message or not message.strip():
		frappe.throw(_("Please enter a message body for the interactive message."))

	if isinstance(buttons, str):
		buttons = json.loads(buttons) if buttons else []
	if isinstance(sections, str):
		sections = json.loads(sections) if sections else []
	buttons = buttons or []
	sections = sections or []

	if interactive_type == "button":
		if not buttons:
			frappe.throw(_("Please add at least one button."))
		if len(buttons) > 3:
			frappe.throw(_("WhatsApp button messages support at most 3 buttons."))
		for btn in buttons:
			if not btn.get("id") or not (btn.get("title") or "").strip():
				frappe.throw(_("Every button needs an id and a title."))
		buttons_payload = {
			"type": "button",
			"buttons": [{"id": btn["id"], "title": btn["title"].strip()} for btn in buttons],
		}
	else:
		if not sections:
			frappe.throw(_("Please add at least one section with options."))
		total_rows = sum(len(section.get("rows") or []) for section in sections)
		if total_rows == 0:
			frappe.throw(_("Please add at least one option to the list."))
		if total_rows > 10:
			frappe.throw(_("WhatsApp list messages support at most 10 options in total."))
		for section in sections:
			if not (section.get("title") or "").strip():
				frappe.throw(_("Every section needs a title."))
			for row in section.get("rows") or []:
				if not row.get("id") or not (row.get("title") or "").strip():
					frappe.throw(_("Every list option needs an id and a title."))
		buttons_payload = {
			"type": "list",
			"list_button_label": (list_button_label or "").strip() or "Select Option",
			"sections": [
				{
					"title": section["title"].strip(),
					"rows": [
						{
							"id": row["id"],
							"title": row["title"].strip(),
							"description": (row.get("description") or "").strip(),
						}
						for row in (section.get("rows") or [])
					],
				}
				for section in sections
			],
		}

	doc = frappe.new_doc("WhatsApp Message")

	if reply_to:
		if not frappe.db.exists("WhatsApp Message", reply_to):
			frappe.throw(_("Referenced WhatsApp message does not exist."), frappe.DoesNotExistError)
		reply_doc = frappe.get_doc("WhatsApp Message", reply_to)
		if not reply_doc.has_permission("read"):
			frappe.throw(
				_("Not permitted to access the referenced WhatsApp message."), frappe.PermissionError
			)
		validate_access(reply_doc.reference_doctype, reply_doc.reference_name)
		doc.update(
			{
				"is_reply": True,
				"reply_to_message_id": reply_doc.message_id,
			}
		)

	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message": message.strip(),
			"to": to,
			"content_type": "interactive",
			"buttons": json.dumps(buttons_payload),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _count_template_placeholders(template_text: str) -> int:
	"""Count the highest {{n}} placeholder index referenced in a template body."""
	if not template_text:
		return 0
	indices = [int(match) for match in re.findall(r"\{\{\s*(\d+)\s*\}\}", template_text)]
	return max(indices) if indices else 0


@frappe.whitelist()
def react_on_whatsapp_message(emoji: str, reply_to_name: str):
	validate_access()
	if not frappe.db.exists("WhatsApp Message", reply_to_name):
		frappe.throw(_("Referenced WhatsApp message does not exist."), frappe.DoesNotExistError)
	reply_to_doc = frappe.get_doc("WhatsApp Message", reply_to_name)

	if not reply_to_doc.has_permission("read"):
		frappe.throw(_("Not permitted to access the referenced WhatsApp message."), frappe.PermissionError)

	validate_access(reply_to_doc.reference_doctype, reply_to_doc.reference_name)

	to = (reply_to_doc.type == "Incoming" and reply_to_doc.get("from")) or reply_to_doc.to
	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reply_to_doc.reference_doctype,
			"reference_name": reply_to_doc.reference_name,
			"message": emoji,
			"to": to,
			"reply_to_message_id": reply_to_doc.message_id,
			"content_type": "reaction",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def mark_whatsapp_messages_read(reference_doctype: str, reference_name: str):
	"""Send WhatsApp read receipts for unread inbound messages on a Lead/Deal.

	Mirrors get_whatsapp_messages' CRM Deal -> linked Lead fan-out, since a
	deal's WhatsApp thread is really the lead's thread carried forward.
	Silently skips accounts/messages that fail (e.g. already read upstream,
	network hiccup) — send_read_receipt itself logs and swallows API errors,
	so a partial failure here shouldn't block the rest of the batch.
	"""
	reference_doc = validate_access(reference_doctype, reference_name)
	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []

	reference_pairs = [(reference_doctype, reference_name)]
	if reference_doctype == "CRM Deal":
		lead = reference_doc.get("lead")
		if lead:
			validate_access("CRM Lead", lead)
			reference_pairs.append(("CRM Lead", lead))

	marked = []
	for ref_doctype, ref_name in reference_pairs:
		unread_names = frappe.get_all(
			"WhatsApp Message",
			filters={
				"reference_doctype": ref_doctype,
				"reference_name": ref_name,
				"type": "Incoming",
				"status": ["!=", "marked as read"],
			},
			pluck="name",
		)
		for name in unread_names:
			doc = frappe.get_doc("WhatsApp Message", name)
			if not doc.message_id:
				continue
			if doc.send_read_receipt():
				marked.append(name)

	return marked


@frappe.whitelist()
def get_whatsapp_templates():
	"""List all synced WhatsApp templates for the management settings page."""
	validate_access()
	if not frappe.db.exists("DocType", "WhatsApp Templates"):
		return []

	return frappe.get_all(
		"WhatsApp Templates",
		fields=[
			"name",
			"template_name",
			"actual_name",
			"category",
			"language",
			"language_code",
			"status",
			"template",
			"header",
			"header_type",
			"footer",
			"sample_values",
			"whatsapp_account",
			"modified",
		],
		order_by="modified desc",
	)


@frappe.whitelist()
def get_whatsapp_flows():
	"""List published WhatsApp Flows available to send, for the compose-time picker.

	Only 'Published' flows are sendable to real users without draft mode
	(unpublished flows would be sent with a "for testing only" draft flag),
	so we only surface those here. Screens are summarized (id + title) so
	the picker can show a lightweight sense of what the flow asks for
	without pulling the full flow_json/fields tables.

	WhatsApp Flow only grants System Manager permissions in frappe_whatsapp
	itself (see whatsapp_flow.json), so Sales User/Manager access is gated
	the same way as get_whatsapp_templates: via validate_access() here,
	with ignore_permissions on the actual read.
	"""
	validate_access()
	if not frappe.db.exists("DocType", "WhatsApp Flow"):
		return []

	flows = frappe.get_all(
		"WhatsApp Flow",
		filters={"status": "Published"},
		fields=["name", "flow_name", "status", "category", "description", "flow_cta", "flow_id", "modified"],
		order_by="modified desc",
		ignore_permissions=True,
	)

	if not flows:
		return flows

	screens = frappe.get_all(
		"WhatsApp Flow Screen",
		filters={"parent": ["in", [f["name"] for f in flows]]},
		fields=["parent", "screen_id", "screen_title", "terminal", "idx"],
		order_by="idx asc",
		ignore_permissions=True,
	)
	screens_by_flow = {}
	for screen in screens:
		screens_by_flow.setdefault(screen["parent"], []).append(screen)

	for flow in flows:
		flow["screens"] = screens_by_flow.get(flow["name"], [])

	return flows


@frappe.whitelist()
def send_whatsapp_flow(reference_doctype: str, reference_name: str, flow: str, to: str, message: str | None = None):
	"""Send a published WhatsApp Flow message to a Lead/Deal's conversation.

	Reuses frappe_whatsapp's own flow-send envelope (WhatsApp Message with
	content_type='flow') rather than reimplementing Meta's interactive/flow
	message shape here — see WhatsAppMessage.send_outgoing()'s 'flow' branch
	in frappe_whatsapp, which builds the interactive.type=flow payload with
	flow_id/flow_token/flow_cta and dispatches it via notify().
	"""
	validate_access(reference_doctype, reference_name)

	if not frappe.db.exists("WhatsApp Flow", flow):
		frappe.throw(_("WhatsApp Flow {0} does not exist.").format(flow), frappe.DoesNotExistError)

	flow_doc = frappe.get_doc("WhatsApp Flow", flow)
	if flow_doc.status != "Published":
		frappe.throw(_("Only published flows can be sent."))
	if not flow_doc.flow_id:
		frappe.throw(_("This flow has not been created on WhatsApp yet."))

	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"content_type": "flow",
			"flow": flow,
			"flow_cta": flow_doc.flow_cta,
			"message": message or "",
			"to": to,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def sync_whatsapp_templates():
	"""Pull the latest template definitions and approval statuses from Meta.

	Delegates to frappe_whatsapp's own WhatsApp Templates.fetch(), which
	upserts local WhatsApp Templates docs for every active WhatsApp Account.
	Requires Sales Manager (not just Sales User) since this triggers an
	outbound call against every configured Meta WhatsApp Business Account.
	"""
	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can sync WhatsApp templates."), frappe.PermissionError)

	if "frappe_whatsapp" not in frappe.get_installed_apps():
		frappe.throw(_("The frappe_whatsapp app is not installed."))

	from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_templates.whatsapp_templates import (
		fetch as fetch_templates_from_meta,
	)

	return fetch_templates_from_meta()


def _require_frappe_whatsapp():
	if "frappe_whatsapp" not in frappe.get_installed_apps():
		frappe.throw(_("The frappe_whatsapp app is not installed."))


@frappe.whitelist()
def get_whatsapp_recipient_lists():
	"""List all WhatsApp Recipient Lists with their recipient counts."""
	validate_access()
	_require_frappe_whatsapp()

	lists = frappe.get_all(
		"WhatsApp Recipient List",
		fields=["name", "list_name", "description", "modified"],
		order_by="modified desc",
	)
	for row in lists:
		row["recipient_count"] = frappe.db.count("WhatsApp Recipient", {"parent": row["name"]})
	return lists


@frappe.whitelist()
def get_whatsapp_recipient_list(name: str):
	"""Get a single WhatsApp Recipient List with its recipient rows."""
	validate_access()
	_require_frappe_whatsapp()

	if not frappe.db.exists("WhatsApp Recipient List", name):
		frappe.throw(_("Recipient List {0} does not exist.").format(name), frappe.DoesNotExistError)

	doc = frappe.get_doc("WhatsApp Recipient List", name)
	return {
		"name": doc.name,
		"list_name": doc.list_name,
		"description": doc.description,
		"recipients": [
			{
				"mobile_number": row.mobile_number,
				"recipient_name": row.recipient_name,
				"recipient_data": row.recipient_data,
			}
			for row in doc.recipients
		],
	}


@frappe.whitelist()
def create_whatsapp_recipient_list(list_name: str, description: str | None = None, recipients: list | str | None = None):
	"""Create a WhatsApp Recipient List from a simple list of {mobile_number, recipient_name} rows."""
	validate_access()
	_require_frappe_whatsapp()

	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can manage WhatsApp recipient lists."), frappe.PermissionError)

	if isinstance(recipients, str):
		recipients = json.loads(recipients) if recipients else []
	recipients = recipients or []

	doc = frappe.new_doc("WhatsApp Recipient List")
	doc.list_name = list_name
	doc.description = description
	for row in recipients:
		mobile_number = (row.get("mobile_number") or "").strip()
		if not mobile_number:
			continue
		doc.append(
			"recipients",
			{
				"mobile_number": mobile_number,
				"recipient_name": row.get("recipient_name"),
				"recipient_data": row.get("recipient_data") or "{}",
			},
		)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_whatsapp_recipient_list(
	name: str, list_name: str, description: str | None = None, recipients: list | str | None = None
):
	"""Update a WhatsApp Recipient List's name, description, and recipient rows."""
	validate_access()
	_require_frappe_whatsapp()

	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can manage WhatsApp recipient lists."), frappe.PermissionError)

	if not frappe.db.exists("WhatsApp Recipient List", name):
		frappe.throw(_("Recipient List {0} does not exist.").format(name), frappe.DoesNotExistError)

	if isinstance(recipients, str):
		recipients = json.loads(recipients) if recipients else []

	doc = frappe.get_doc("WhatsApp Recipient List", name)
	doc.list_name = list_name
	doc.description = description
	if recipients is not None:
		doc.recipients = []
		for row in recipients:
			mobile_number = (row.get("mobile_number") or "").strip()
			if not mobile_number:
				continue
			doc.append(
				"recipients",
				{
					"mobile_number": mobile_number,
					"recipient_name": row.get("recipient_name"),
					"recipient_data": row.get("recipient_data") or "{}",
				},
			)
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def delete_whatsapp_recipient_list(name: str):
	"""Delete a WhatsApp Recipient List."""
	validate_access()
	_require_frappe_whatsapp()

	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can manage WhatsApp recipient lists."), frappe.PermissionError)

	if not frappe.db.exists("WhatsApp Recipient List", name):
		frappe.throw(_("Recipient List {0} does not exist.").format(name), frappe.DoesNotExistError)

	if frappe.db.exists("Bulk WhatsApp Message", {"recipient_list": name, "docstatus": ["!=", 2]}):
		frappe.throw(_("This recipient list is used by one or more bulk campaigns and cannot be deleted."))

	frappe.delete_doc("WhatsApp Recipient List", name, ignore_permissions=True)


@frappe.whitelist()
def get_bulk_whatsapp_messages():
	"""List past/ongoing bulk WhatsApp campaigns for the settings history table."""
	validate_access()
	_require_frappe_whatsapp()

	return frappe.get_all(
		"Bulk WhatsApp Message",
		fields=[
			"name",
			"title",
			"docstatus",
			"status",
			"recipient_type",
			"recipient_list",
			"recipient_count",
			"sent_count",
			"template",
			"use_template",
			"scheduled_time",
			"whatsapp_account",
			"modified",
			"owner",
		],
		order_by="modified desc",
		limit_page_length=100,
	)


@frappe.whitelist()
def get_bulk_whatsapp_message_progress(name: str):
	"""Get live send progress (sent/failed/queued counts) for a bulk campaign."""
	validate_access()
	_require_frappe_whatsapp()

	if not frappe.db.exists("Bulk WhatsApp Message", name):
		frappe.throw(_("Bulk WhatsApp Message {0} does not exist.").format(name), frappe.DoesNotExistError)

	doc = frappe.get_doc("Bulk WhatsApp Message", name)
	return doc.get_progress()


@frappe.whitelist()
def retry_failed_bulk_whatsapp_messages(name: str):
	"""Requeue failed sends within a bulk campaign for re-sending."""
	validate_access()
	_require_frappe_whatsapp()

	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can retry WhatsApp campaigns."), frappe.PermissionError)

	if not frappe.db.exists("Bulk WhatsApp Message", name):
		frappe.throw(_("Bulk WhatsApp Message {0} does not exist.").format(name), frappe.DoesNotExistError)

	doc = frappe.get_doc("Bulk WhatsApp Message", name)
	doc.retry_failed()
	return True


@frappe.whitelist()
def create_bulk_whatsapp_campaign(
	title: str,
	template: str,
	recipient_list: str,
	whatsapp_account: str | None = None,
	template_variables: list | str | None = None,
	scheduled_time: str | None = None,
	attach: str | None = None,
):
	"""Create and submit a Bulk WhatsApp Message campaign against a Recipient List.

	Template parameters are applied uniformly to every recipient (variable_type
	'Common'). Per-recipient values are already supported by frappe_whatsapp
	via each WhatsApp Recipient row's `recipient_data` JSON (variable_type
	'Unique') — set those values when building/editing the recipient list
	itself rather than here, since a single campaign form can't reasonably
	ask a manager to fill out N different rows of the same parameters.
	"""
	validate_access()
	_require_frappe_whatsapp()

	if not any(role in ["System Manager", "Sales Manager"] for role in frappe.get_roles()):
		frappe.throw(_("Only sales managers can send bulk WhatsApp campaigns."), frappe.PermissionError)

	if not frappe.db.exists("WhatsApp Templates", template):
		frappe.throw(_("WhatsApp Template {0} does not exist.").format(template), frappe.DoesNotExistError)

	if not frappe.db.exists("WhatsApp Recipient List", recipient_list):
		frappe.throw(
			_("Recipient List {0} does not exist.").format(recipient_list), frappe.DoesNotExistError
		)

	recipient_count = frappe.db.count("WhatsApp Recipient", {"parent": recipient_list})
	if not recipient_count:
		frappe.throw(_("Selected recipient list has no recipients."))

	if isinstance(template_variables, str):
		template_variables = json.loads(template_variables) if template_variables else []
	template_variables = template_variables or []

	template_doc = frappe.get_doc("WhatsApp Templates", template)
	expected_body_params = _count_template_placeholders(template_doc.template)
	if len(template_variables) < expected_body_params or any(not p for p in template_variables[:expected_body_params]):
		frappe.throw(
			_(
				"This template expects {0} body parameter(s), but {1} were provided. "
				"Please fill in all template parameters before sending."
			).format(expected_body_params, len(template_variables))
		)

	doc = frappe.new_doc("Bulk WhatsApp Message")
	doc.title = title
	doc.recipient_type = "Recipient List"
	doc.recipient_list = recipient_list
	doc.use_template = 1
	doc.template = template
	doc.variable_type = "Common"
	if template_variables:
		# WhatsAppRecipient.recipient_data (used for the Unique-variable path)
		# is a JSON object, so mirror that shape here for the Common path too
		# rather than a bare list — bulk_whatsapp_message.py's
		# create_single_message() only special-cases variable_type=='Unique'
		# for recipient_data, so template_variables can stay a JSON object
		# of "1", "2", ... keys matching {{1}}, {{2}}, ... placeholders.
		doc.template_variables = json.dumps({str(i + 1): value for i, value in enumerate(template_variables)})
	if attach:
		doc.attach = attach
	if whatsapp_account:
		doc.whatsapp_account = whatsapp_account
	if scheduled_time:
		doc.scheduled_time = scheduled_time

	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def parse_template_parameters(string, parameters):
	for i, parameter in enumerate(parameters, start=1):
		placeholder = "{{" + str(i) + "}}"
		string = string.replace(placeholder, str(parameter))

	return string


def get_from_name(message):
	doc = frappe.get_doc(message["reference_doctype"], message["reference_name"])
	from_name = ""
	if message["reference_doctype"] == "CRM Deal":
		if doc.get("contacts"):
			for c in doc.get("contacts"):
				if c.is_primary:
					from_name = c.full_name or c.mobile_no
					break
		else:
			from_name = doc.get("lead_name")
	else:
		from_name = " ".join(name for name in [doc.get("first_name"), doc.get("last_name")] if name)
	return from_name


def add_roles():
	if "frappe_whatsapp" not in frappe.get_installed_apps():
		return

	role_list = ["Sales Manager", "Sales User"]
	doctypes = ["WhatsApp Message", "WhatsApp Templates", "WhatsApp Settings"]
	for doctype in doctypes:
		for role in role_list:
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				continue
			add_permission(doctype, role, 0, "write")
			update_permission_property(doctype, role, 0, "create", 1)
			update_permission_property(doctype, role, 0, "delete", 1)
			update_permission_property(doctype, role, 0, "share", 1)
			update_permission_property(doctype, role, 0, "email", 1)
			update_permission_property(doctype, role, 0, "print", 1)
			update_permission_property(doctype, role, 0, "report", 1)
			update_permission_property(doctype, role, 0, "export", 1)
