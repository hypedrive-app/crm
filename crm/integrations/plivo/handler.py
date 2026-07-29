import frappe
import requests
from frappe import _
from frappe.integrations.utils import create_request_log
from werkzeug.wrappers import Response

from crm.integrations.api import get_contact_by_phone_number

# Endpoints for webhook

# Call answered (outgoing calls we placed via make_a_call):
# <site>/api/method/crm.integrations.plivo.handler.handle_answer?key=<plivo-webhook-verify-token>

# Call hung up:
# <site>/api/method/crm.integrations.plivo.handler.handle_hangup?key=<plivo-webhook-verify-token>

# Recording ready (fired once Record/ finishes, only when record_call is enabled):
# <site>/api/method/crm.integrations.plivo.handler.handle_recording?key=<plivo-webhook-verify-token>

# Plivo Reference:
# https://www.plivo.com/docs/voice/api/call/make-a-call
# https://www.plivo.com/docs/voice/concepts/callbacks
# https://www.plivo.com/docs/voice/xml/dial


# Call answered — Plivo POSTs here once the outbound leg connects. We respond
# with Dial XML that bridges the call to the agent's own phone (Exotel-style:
# the agent's real mobile rings first, then gets bridged) and, if recording
# is enabled, kick off Plivo's separate Record API (Plivo has no "Record: true"
# flag on the initial Call/ request the way Exotel/Twilio do — recording is a
# second call against Call/{call_uuid}/Record/ made once the call is live).
@frappe.whitelist(allow_guest=True)
def handle_answer(**kwargs):
	validate_request()
	if not is_integration_enabled():
		return _empty_response()

	request_log = create_request_log(
		kwargs,
		request_description="Plivo Call Answer",
		service_name="Plivo",
		request_headers=frappe.request.headers,
		is_remote_request=1,
	)

	try:
		request_log.status = "Completed"
		call_payload = kwargs
		frappe.publish_realtime("plivo_call", call_payload)

		call_uuid = call_payload.get("CallUUID")
		# The agent's own phone number to bridge into, passed through as a query
		# param on the answer_url we built in make_a_call (Plivo echoes the query
		# string through to this callback's form/query args, same trick used for
		# `key`) — see get_callback_url/make_a_call.
		agent_number = frappe.request.args.get("dial_to")

		existing_log = get_call_log(call_payload)
		if existing_log:
			update_call_log(call_payload, call_log=existing_log, status="In Progress")
		else:
			create_call_log(
				call_id=call_uuid,
				from_number=call_payload.get("From"),
				to_number=call_payload.get("To"),
				medium=call_payload.get("To"),
				status="In Progress",
				call_type="Outgoing",
				agent=frappe.session.user if frappe.session.user != "Guest" else None,
			)

		if frappe.db.get_single_value("CRM Plivo Settings", "record_call"):
			start_recording(call_uuid)

		return _dial_response(agent_number) if agent_number else _empty_response()
	except Exception:
		request_log.status = "Failed"
		request_log.error = frappe.get_traceback()
		frappe.db.rollback()
		frappe.log_error(title="Error while handling Plivo answer callback")
		frappe.db.commit()
		return _empty_response()
	finally:
		request_log.save(ignore_permissions=True)
		frappe.db.commit()


# Call hung up — final status/duration lands here.
@frappe.whitelist(allow_guest=True)
def handle_hangup(**kwargs):
	validate_request()
	if not is_integration_enabled():
		return

	request_log = create_request_log(
		kwargs,
		request_description="Plivo Call Hangup",
		service_name="Plivo",
		request_headers=frappe.request.headers,
		is_remote_request=1,
	)

	try:
		request_log.status = "Completed"
		call_payload = kwargs
		frappe.publish_realtime("plivo_call", call_payload)

		if call_log := get_call_log(call_payload):
			update_call_log(call_payload, call_log=call_log)
		else:
			create_call_log(
				call_id=call_payload.get("CallUUID"),
				from_number=call_payload.get("From"),
				to_number=call_payload.get("To"),
				medium=call_payload.get("To"),
				status=get_call_log_status(call_payload),
			)
	except Exception:
		request_log.status = "Failed"
		request_log.error = frappe.get_traceback()
		frappe.db.rollback()
		frappe.log_error(title="Error while handling Plivo hangup callback")
		frappe.db.commit()
	finally:
		request_log.save(ignore_permissions=True)
		frappe.db.commit()


# Recording ready — fired by Plivo's Record API's own callback_url once the
# recording is available (separate from the call-status webhooks above).
@frappe.whitelist(allow_guest=True)
def handle_recording(**kwargs):
	validate_request()
	if not is_integration_enabled():
		return

	try:
		call_uuid = kwargs.get("CallUUID")
		recording_url = kwargs.get("RecordUrl")
		if not (call_uuid and recording_url):
			return

		if call_log := frappe.db.exists("CRM Call Log", call_uuid):
			frappe.db.set_value("CRM Call Log", call_log, "recording_url", recording_url)
			frappe.db.commit()
	except Exception:
		frappe.log_error(title="Error while handling Plivo recording callback")
		frappe.db.commit()


# Outgoing Call
@frappe.whitelist()
def make_a_call(to_number: str, from_number: str | None = None, caller_id: str | None = None):
	if not is_integration_enabled():
		frappe.throw(_("Please setup Plivo integration"), title=_("Integration Not Enabled"))

	if not from_number:
		from_number = frappe.get_value("CRM Telephony Agent", {"user": frappe.session.user}, "mobile_no")

	if not caller_id:
		caller_id = frappe.get_value("CRM Telephony Agent", {"user": frappe.session.user}, "plivo_number")

	if not caller_id:
		frappe.throw(
			_("You do not have a Plivo Number set in your Telephony Agent"), title=_("Plivo Number Missing")
		)

	if not from_number:
		frappe.throw(
			_("You do not have mobile number set in your Telephony Agent"), title=_("Mobile Number Missing")
		)

	settings = get_plivo_settings()
	endpoint = f"https://api.plivo.com/v1/Account/{settings.auth_id}/Call/"

	try:
		response = requests.post(
			endpoint,
			auth=(settings.auth_id, settings.get_password("auth_token")),
			json={
				"from": caller_id,
				"to": to_number,
				"answer_url": get_callback_url("handle_answer") + f"&dial_to={from_number}",
				"answer_method": "POST",
				"hangup_url": get_callback_url("handle_hangup"),
				"hangup_method": "POST",
			},
		)
		response.raise_for_status()
	except requests.exceptions.HTTPError:
		error = response.json().get("error") or response.text
		frappe.throw(str(error), title=_("Plivo Exception"))
	else:
		res = response.json()

		call_log = create_call_log(
			call_id=res.get("request_uuid"),
			from_number=caller_id,
			to_number=to_number,
			medium=caller_id,
			call_type="Outgoing",
			status="Initiated",
			agent=frappe.session.user,
		)
		# make_a_call's response only carries request_uuid (assigned before the
		# call legs exist); Plivo swaps in the real CallUUID on the answer/hangup
		# callbacks, so the call log's `id` gets reconciled there via
		# get_call_log's request_uuid fallback below.
		return {"CallSid": call_log.id, "request_uuid": res.get("request_uuid")}


def _dial_response(number: str) -> Response:
	xml = f"<Response><Dial><Number>{frappe.utils.escape_html(number)}</Number></Dial></Response>"
	return Response(xml, mimetype="text/xml")


def _empty_response() -> Response:
	return Response("<Response></Response>", mimetype="text/xml")


def start_recording(call_uuid: str):
	settings = get_plivo_settings()
	endpoint = f"https://api.plivo.com/v1/Account/{settings.auth_id}/Call/{call_uuid}/Record/"
	try:
		requests.post(
			endpoint,
			auth=(settings.auth_id, settings.get_password("auth_token")),
			json={"callback_url": get_callback_url("handle_recording"), "callback_method": "POST"},
			timeout=10,
		)
	except requests.exceptions.RequestException:
		# Recording is best-effort — a failed Record/ call shouldn't fail the
		# call itself, just leaves the CRM Call Log without a recording_url.
		frappe.log_error(title="Error while starting Plivo call recording")


def get_callback_url(method: str) -> str:
	from frappe.utils.data import get_url

	webhook_verify_token = frappe.db.get_single_value("CRM Plivo Settings", "webhook_verify_token")
	return get_url(f"api/method/crm.integrations.plivo.handler.{method}?key={webhook_verify_token}")


def get_plivo_settings():
	return frappe.get_single("CRM Plivo Settings")


def validate_request():
	# Same workaround as crm.integrations.exotel.handler.validate_request: Plivo
	# webhooks aren't request-signed the way Twilio's are (Plivo does support
	# X-Plivo-Signature-V3, but validating it needs the exact raw request URL as
	# Plivo saw it, which is unreliable behind Dokploy/Traefik's proxy chain —
	# same reasoning that led Exotel's integration to a shared-secret query
	# param instead). Mirroring that choice here for consistency.
	webhook_verify_token = frappe.db.get_single_value("CRM Plivo Settings", "webhook_verify_token")
	key = frappe.request.args.get("key")
	is_valid = key and key == webhook_verify_token

	if not is_valid:
		frappe.throw(_("Unauthorized request"), exc=frappe.PermissionError)


@frappe.whitelist()
def is_integration_enabled():
	return frappe.db.get_single_value("CRM Plivo Settings", "enabled", True)


# Call Log Functions
def create_call_log(
	call_id,
	from_number,
	to_number,
	medium,
	agent=None,
	status="Ringing",
	call_type="Incoming",
):
	call_log = frappe.new_doc("CRM Call Log")
	call_log.id = call_id
	call_log.to = to_number
	call_log.medium = medium
	call_log.type = call_type
	call_log.status = status
	call_log.telephony_medium = "Plivo"
	setattr(call_log, "from", from_number)

	if call_type == "Incoming":
		call_log.receiver = agent
	else:
		call_log.caller = agent

	contact_number = from_number if call_type == "Incoming" else to_number
	link(contact_number, call_log)

	call_log.save(ignore_permissions=True)
	frappe.db.commit()
	return call_log


def link(contact_number, call_log):
	contact = get_contact_by_phone_number(contact_number)
	if contact.get("name"):
		doctype = "Contact"
		docname = contact.get("name")
		if contact.get("lead"):
			doctype = "CRM Lead"
			docname = contact.get("lead")
		elif contact.get("deal"):
			doctype = "CRM Deal"
			docname = contact.get("deal")
		call_log.link_with_reference_doc(doctype, docname)


def get_call_log(call_payload):
	call_uuid = call_payload.get("CallUUID")
	if call_uuid and frappe.db.exists("CRM Call Log", call_uuid):
		return frappe.get_doc("CRM Call Log", call_uuid)

	# make_a_call only has request_uuid to name the log with (CallUUID doesn't
	# exist until Plivo's answer/hangup callback); reconcile onto the real
	# CallUUID the first time a callback for this request_uuid arrives.
	request_uuid = call_payload.get("RequestUUID")
	if request_uuid and (name := frappe.db.exists("CRM Call Log", request_uuid)):
		call_log = frappe.get_doc("CRM Call Log", name)
		if call_uuid and call_uuid != call_log.id:
			frappe.rename_doc("CRM Call Log", call_log.name, call_uuid, force=True)
			call_log = frappe.get_doc("CRM Call Log", call_uuid)
		return call_log


def get_call_log_status(call_payload):
	status = call_payload.get("CallStatus")
	mapping = {
		"ringing": "Ringing",
		"in-progress": "In Progress",
		"completed": "Completed",
		"busy": "Ringing",
		"no-answer": "No Answer",
		"failed": "Failed",
		"canceled": "Canceled",
		"timeout": "No Answer",
	}
	return mapping.get(status, "Completed")


def update_call_log(call_payload, status=None, call_log=None):
	call_log = call_log or get_call_log(call_payload)
	status = status or get_call_log_status(call_payload)
	try:
		if call_log:
			call_log.status = status
			call_log.start_time = call_payload.get("StartTime") or call_log.start_time
			call_log.end_time = call_payload.get("EndTime")

			if call_log.start_time and call_log.end_time:
				call_log.duration = frappe.utils.time_diff_in_seconds(
					call_log.end_time, call_log.start_time
				)

			call_log.save(ignore_permissions=True)
			frappe.db.commit()
			return call_log
	except Exception:
		frappe.log_error(title="Error while updating Plivo call record")
		frappe.db.commit()
