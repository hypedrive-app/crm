"""CRM-side Chatwoot integration surface.

Mirrors crm/api/whatsapp.py's exact contract shape (is_X_installed /
is_X_enabled / get_X_messages / validate_access), except every read here
proxies LIVE to Chatwoot's REST API via frappe_chatwoot's whitelisted API
(frappe_chatwoot.frappe_chatwoot.api.chatwoot) instead of running frappe.get_all against a
locally-duplicated message doctype — frappe_chatwoot ships no such doctype
by design (Chatwoot itself stays the system of record for conversation
state; see frappe_chatwoot/README.md).

CRM has zero import-time dependency on frappe_chatwoot's internals beyond
calling its whitelisted, string-addressed functions — same "generic Frappe
API, no cross-app import" posture crm/api/whatsapp.py takes toward
frappe_whatsapp.
"""

import frappe
from frappe import _

ALLOWED_CHATWOOT_ROLES = ["System Manager", "Sales Manager", "Sales User"]


def validate_access(reference_doctype=None, reference_name=None, permtype="read"):
	if not any(role in ALLOWED_CHATWOOT_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access Chatwoot features."), frappe.PermissionError)

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


@frappe.whitelist()
def is_chatwoot_installed():
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		return False
	return True


@frappe.whitelist()
def is_chatwoot_enabled():
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		return False
	enabled = frappe.get_cached_value("Chatwoot Settings", "Chatwoot Settings", "enabled")
	base_url = frappe.get_cached_value("Chatwoot Settings", "Chatwoot Settings", "base_url")
	return bool(enabled) and bool(base_url)


@frappe.whitelist()
def get_chatwoot_conversations(reference_doctype: str, reference_name: str):
	"""Live conversation list for a Lead/Deal, proxied straight through to
	frappe_chatwoot (which itself resolves the Chatwoot contact by
	phone/email search — see that app's api/chatwoot.py docstring)."""
	validate_access(reference_doctype, reference_name)
	if "twilio_integration" in frappe.get_installed_apps():
		return []
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		return []

	from frappe_chatwoot.frappe_chatwoot.api.chatwoot import get_conversations_for_contact

	return get_conversations_for_contact(reference_doctype, reference_name)


def _validate_conversation_ownership(reference_doctype: str, reference_name: str, conversation_id: int):
	"""frappe_chatwoot.get_messages/get_new_messages/send_message intentionally
	skip reference-doc permission checks (a conversation_id alone carries no
	reference-doc context — see that module's get_messages docstring) and
	defer enforcement to the caller, on the assumption CRM only ever passes
	through conversation_ids it obtained from get_conversations_for_contact.
	That contract wasn't actually enforced here: this closes it by requiring
	reference_doctype/reference_name on every conversation_id-keyed call,
	running the same role+doc-permission check get_chatwoot_conversations
	uses, and confirming conversation_id is one of THAT reference's live
	conversations before proxying through — otherwise any authenticated
	sales user could read or send into an arbitrary conversation just by
	guessing/observing its numeric id."""
	validate_access(reference_doctype, reference_name)

	from frappe_chatwoot.frappe_chatwoot.api.chatwoot import get_conversations_for_contact

	conversation_id = frappe.utils.cint(conversation_id)
	owned_ids = {frappe.utils.cint(c["id"]) for c in get_conversations_for_contact(reference_doctype, reference_name)}
	if conversation_id not in owned_ids:
		frappe.throw(
			_("Not permitted to access this conversation."),
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_chatwoot_messages(
	reference_doctype: str, reference_name: str, conversation_id: int, before: int = None
):
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		return {"meta": {}, "messages": []}

	_validate_conversation_ownership(reference_doctype, reference_name, conversation_id)

	from frappe_chatwoot.frappe_chatwoot.api.chatwoot import get_messages

	return get_messages(conversation_id, before=before)


@frappe.whitelist()
def get_new_chatwoot_messages(
	reference_doctype: str, reference_name: str, conversation_id: int, since_id: int = None
):
	"""Incremental poll proxy — used on realtime ('chatwoot_message' socket
	event) refetch so an active thread only pulls what's new instead of the
	full message history on every poll tick. See
	frappe_chatwoot.frappe_chatwoot.api.chatwoot.get_new_messages for the bounded drain-loop
	contract (truncated=True means call again immediately)."""
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		return {"messages": [], "meta": {}, "max_id_seen": since_id, "truncated": False}

	_validate_conversation_ownership(reference_doctype, reference_name, conversation_id)

	from frappe_chatwoot.frappe_chatwoot.api.chatwoot import get_new_messages

	return get_new_messages(conversation_id, since_id=since_id)


@frappe.whitelist()
def send_chatwoot_message(reference_doctype: str, reference_name: str, conversation_id: int, content: str):
	if not frappe.db.exists("DocType", "Chatwoot Settings"):
		frappe.throw(_("Chatwoot integration is not installed."))

	_validate_conversation_ownership(reference_doctype, reference_name, conversation_id)

	from frappe_chatwoot.frappe_chatwoot.api.chatwoot import send_message

	return send_message(conversation_id, content)


def add_roles():
	"""Registered in crm/hooks.py's after_migrate, mirroring
	crm.api.whatsapp.add_roles exactly: grant CRM's own sales roles explicit
	Custom DocPerm rows on frappe_chatwoot's Settings doctype, since
	frappe_chatwoot's own doctype JSON only grants System Manager by
	default."""
	if "frappe_chatwoot" not in frappe.get_installed_apps():
		return

	from frappe.permissions import add_permission, update_permission_property

	role_list = ["Sales Manager", "Sales User"]
	doctypes = ["Chatwoot Settings"]
	for doctype in doctypes:
		for role in role_list:
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				continue
			add_permission(doctype, role, 0, "read")
