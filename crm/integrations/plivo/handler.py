from urllib.parse import quote

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


# Call answered — Plivo invokes the Application's answer_url in TWO distinct
# situations that both land here, and this callback has to tell them apart:
#
#  1. Server-initiated (make_a_call/Exotel-style): we already know the
#     destination (the agent's own phone, passed through as `dial_to` on the
#     answer_url we built) — bridge with <Dial><Number>{agent's phone}</Number>.
#
#  2. Browser-SDK-initiated (client.call(number) from PlivoCallUI's browser
#     leg): the endpoint itself is the caller, so there's no `dial_to` query
#     param — Plivo's own docs confirm the SDK's outbound flow still requires
#     us to answer with <Dial><Number>{destination}</Number> (not automatic,
#     see plivo.com/docs/voice/sdk/browser/overview), with `To` in the
#     payload carrying the number the agent dialed. We recognize this case by
#     checking whether `From` matches a known agent's plivo_endpoint_username
#     (a value WE assigned when provisioning the endpoint — see
#     get_browser_calling_credentials — so this disambiguation doesn't depend
#     on guessing an undocumented Plivo-internal field). This case ALSO needs
#     an explicit callerId on the Dial (see below) — an Endpoint has no phone
#     number of its own to present to the PSTN network.
#
#     IMPORTANT — do NOT use `Direction`/`CallDirection` to distinguish these
#     two cases: a Plivo engineer confirmed (github.com/plivo/
#     plivo-browser-sdk2-examples/issues/3) that for an Endpoint-originated
#     call, the leg hitting answer_url is the endpoint->Plivo leg, which
#     Plivo itself reports as Direction="inbound" — the OPPOSITE of the
#     intuitive guess. A Direction=="outbound" check here would silently
#     misclassify every real browser call as server-initiated.
#
# Recording (if enabled) is a separate Plivo API call kicked off here either
# way — Plivo has no "Record: true" flag on the initial request the way
# Exotel/Twilio do; recording only starts via a second POST against
# Call/{call_uuid}/Record/ made once the call is confirmed live.
#
# Resolving the real agent: this webhook always hits as Guest (Plivo's
# callbacks are unauthenticated — see validate_request), so
# frappe.session.user is never the initiating agent and can't be used for
# CRM Call Log's caller field. Both cases above already have the real
# answer independent of session:
#  - server-initiated: the agent who called make_a_call is threaded through
#    explicitly via an `agent` query param on the answer_url (alongside the
#    existing `dial_to`), so it's just read back here.
#  - browser-originated: the endpoint username already resolved above (to
#    find agent_plivo_number) belongs to exactly one CRM Telephony Agent,
#    whose `user` field IS the initiating agent — reused from the same
#    lookup rather than re-queried.
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
		dial_target = frappe.request.args.get("dial_to")
		# The user who initiated the call — for server-initiated calls this is
		# threaded through the answer_url query string at creation time (see
		# make_a_call, which appends `&agent=` alongside the existing `&dial_to=`),
		# since this webhook itself always hits as Guest (Plivo's callbacks
		# aren't authenticated) and frappe.session.user is therefore never the
		# real agent. For browser-originated calls this gets overwritten below
		# once the endpoint username resolves to a CRM Telephony Agent.
		agent_user = frappe.request.args.get("agent")
		is_browser_originated = False
		agent_plivo_number = None

		if not dial_target:
			# Confirmed live (2026-07-29 test call): Plivo reports From as a full
			# `sip:<endpoint_username>@phone.plivo.com` URI for endpoint-originated
			# calls, NOT the bare username — comparing the raw value against our
			# stored plivo_endpoint_username always failed silently (fell through
			# to the "unrecognized" branch below) until this was extracted.
			caller = extract_endpoint_username(call_payload.get("From"))
			if caller:
				agent_plivo_number, agent_user = frappe.db.get_value(
					"CRM Telephony Agent", {"plivo_endpoint_username": caller}, ["plivo_number", "user"]
				) or (None, None)
			if agent_plivo_number:
				is_browser_originated = True
				dial_target = call_payload.get("To")

		# For browser-originated calls, `From` is the Plivo Endpoint's sip: URI,
		# not a real phone number — the CRM Call Log's "From Number" shows the
		# agent's own Plivo number instead (already resolved above).
		log_from_number = agent_plivo_number if is_browser_originated else call_payload.get("From")

		existing_log = get_call_log(call_payload)
		if existing_log:
			update_call_log(call_payload, call_log=existing_log, status="In Progress")
		else:
			create_call_log(
				call_id=call_uuid,
				from_number=log_from_number,
				to_number=call_payload.get("To"),
				medium=call_payload.get("To"),
				status="In Progress",
				call_type="Outgoing",
				agent=agent_user,
			)

		if frappe.db.get_single_value("CRM Plivo Settings", "record_call"):
			start_recording(call_uuid)

		if not dial_target:
			# Neither a recognized server-initiated call (has dial_to) nor a
			# recognized browser-originated one (From matches a provisioned
			# endpoint username) — genuinely unexpected shape. Log it via the
			# request_log above (already captures the full payload) rather than
			# silently guessing at a destination.
			frappe.log_error(
				title="Plivo answer callback: could not resolve dial target",
				message=frappe.as_json(call_payload),
			)
			return _empty_response()

		# callerId is mandatory here, not cosmetic: Plivo's own <Dial> reference
		# (plivo.com/docs/voice/xml/dial) documents that when callerId is
		# omitted, Plivo falls back to "caller's ID" — for an Endpoint-originated
		# leg that identity is the SIP endpoint itself, which is not a number
		# the PSTN network can present as caller ID. Confirmed live: omitting
		# callerId on a browser-originated call produced an immediate "Busy"
		# from the carrier on every attempt (2026-07-29). Server-initiated
		# calls don't hit this because their From is already a real Plivo
		# number (the caller_id make_a_call posted to Plivo directly).
		caller_id = agent_plivo_number if is_browser_originated else None
		return _dial_response(dial_target, caller_id=caller_id)
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

		# Recording's own callback_url (registered in start_recording) is
		# unreliable in practice — confirmed live (2026-07-29): Plivo's Record/
		# API accepts the request and genuinely records the call (verified via
		# GET /Recording/, which lists the finished file with a real
		# recording_url), but the completion webhook itself never arrives —
		# zero "Plivo Call Recording" Integration Request log entries across
		# multiple real test calls, despite the answer/hangup webhooks for the
		# same calls working correctly. Rather than depend on a callback that
		# doesn't fire, poll Plivo's own Recording list for this call_uuid
		# instead — a background job (not a blocking sleep in the webhook
		# response) since the recording file isn't ready the instant the call
		# ends.
		if frappe.db.get_single_value("CRM Plivo Settings", "record_call"):
			frappe.enqueue(
				fetch_recording_url,
				queue="short",
				call_uuid=call_payload.get("CallUUID"),
				enqueue_after_commit=True,
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


def fetch_recording_url(call_uuid: str, max_attempts: int = 6, delay_seconds: int = 10):
	"""Poll Plivo's Recording list for call_uuid and persist recording_url onto
	the matching CRM Call Log once found. Plivo needs a few seconds to finish
	processing/uploading the recording after hangup, so this retries with a
	fixed delay between attempts rather than assuming it's ready on the first
	check. Runs entirely inside a background worker (enqueued via
	handle_hangup with enqueue_after_commit=True) — the sleep here does not
	block the webhook response or any web request."""
	import time

	settings = get_plivo_settings()

	for attempt in range(1, max_attempts + 1):
		if not frappe.db.exists("CRM Call Log", call_uuid):
			return

		try:
			response = requests.get(
				f"https://api.plivo.com/v1/Account/{settings.auth_id}/Recording/",
				auth=(settings.auth_id, settings.get_password("auth_token")),
				params={"call_uuid": call_uuid},
				timeout=10,
			)
			response.raise_for_status()
			recordings = response.json().get("objects") or []
		except requests.exceptions.RequestException:
			recordings = []

		if recordings:
			frappe.db.set_value(
				"CRM Call Log", call_uuid, "recording_url", recordings[0]["recording_url"]
			)
			frappe.db.commit()
			return

		if attempt < max_attempts:
			time.sleep(delay_seconds)

	frappe.log_error(
		title="Plivo recording never appeared",
		message=f"call_uuid={call_uuid}, gave up after {max_attempts} attempts",
	)


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


# Browser (WebRTC) calling — auto-provisioning
# Rather than asking every agent to create a Plivo Endpoint by hand in
# Plivo's own console and paste the username/password back in (the manual
# flow Plivo's docs describe), the CRM provisions one Endpoint per agent
# server-side the first time they enable browser calling, the same
# zero-manual-setup bar Twilio's generate_access_token already sets here.
# Endpoint credentials, once created, are reused indefinitely — Plivo's
# create-endpoint response never echoes the password back, so it has to be
# generated here and persisted (encrypted, via the Password fieldtype) rather
# than re-derived on every call.
@frappe.whitelist()
def get_browser_calling_credentials():
	"""Returns {app_id, username, password} for the current user's Plivo
	Endpoint, creating one (and linking it to the configured Application) on
	first use. Frontend passes username/password straight to the Browser
	SDK's Client.login()."""
	settings = get_plivo_settings()
	if not (settings.enabled and settings.browser_calling_enabled):
		frappe.throw(_("Browser calling is not enabled"), title=_("Integration Not Enabled"))

	if not settings.application_id:
		frappe.throw(
			_("Plivo Application ID is not configured"), title=_("Browser Calling Not Configured")
		)

	agent_name = frappe.db.exists("CRM Telephony Agent", {"user": frappe.session.user})
	if not agent_name:
		frappe.throw(
			_("You do not have a Telephony Agent record set up"), title=_("Telephony Agent Missing")
		)

	agent = frappe.get_doc("CRM Telephony Agent", agent_name)

	if not agent.plivo_endpoint_username:
		_provision_endpoint(agent, settings)

	return {
		"app_id": settings.application_id,
		"username": agent.plivo_endpoint_username,
		"password": agent.get_password("plivo_endpoint_password"),
	}


def _provision_endpoint(agent, settings):
	import secrets
	import string

	# Plivo appends its own 12-digit suffix to whatever username we submit, so
	# a simple session.user-derived alias is enough — Plivo guarantees the
	# final username is unique account-wide, not us. Plivo also requires the
	# username to start with a letter, so a leading digit (possible if
	# agent.user starts with one, e.g. "2fa-backup@...") gets a prefix rather
	# than being submitted as-is and rejected.
	base_username = "".join(ch for ch in agent.user.split("@")[0] if ch.isalnum()) or "agent"
	if base_username[0].isdigit():
		base_username = "agent" + base_username
	base_username = base_username[:20]
	password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))

	# Plivo restricts the alias to "Letters, Numbers, . + @ - _" — it rejects a
	# space (and anything else outside that set) with a 400. `user_name` is a
	# free-text display name that very often contains a space ("Shivam Gupta"),
	# so it can't be sent raw the way it was, or every such agent's browser
	# calling fails to provision. Sanitize to the allowed set, collapsing
	# spaces to underscores, and fall back to the (already-safe) derived
	# username if nothing usable remains.
	raw_alias = agent.user_name or agent.user
	alias = "".join(
		ch if (ch.isalnum() or ch in ".+@-_") else ("_" if ch == " " else "")
		for ch in raw_alias
	)
	alias = (alias.strip("_") or base_username)[:64]

	response = requests.post(
		f"https://api.plivo.com/v1/Account/{settings.auth_id}/Endpoint/",
		auth=(settings.auth_id, settings.get_password("auth_token")),
		json={
			"username": base_username,
			"password": password,
			"alias": alias,
			"app_id": settings.application_id,
		},
	)
	try:
		response.raise_for_status()
	except requests.exceptions.HTTPError:
		error = response.json().get("error") or response.text
		frappe.throw(str(error), title=_("Failed to provision Plivo Endpoint"))

	res = response.json()
	agent.plivo_endpoint_username = res.get("username")
	agent.plivo_endpoint_password = password
	agent.save(ignore_permissions=True)
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
				"answer_url": get_callback_url("handle_answer")
				+ f"&dial_to={quote(from_number)}&agent={quote(frappe.session.user)}",
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


def _dial_response(number: str, caller_id: str | None = None) -> Response:
	dial_attrs = f' callerId="{frappe.utils.escape_html(caller_id)}"' if caller_id else ""
	xml = (
		f"<Response><Dial{dial_attrs}>"
		f"<Number>{frappe.utils.escape_html(number)}</Number>"
		f"</Dial></Response>"
	)
	return Response(xml, mimetype="text/xml")


def _empty_response() -> Response:
	return Response("<Response></Response>", mimetype="text/xml")


def extract_endpoint_username(from_value: str | None) -> str | None:
	"""Plivo reports an Endpoint-originated call's From as a full SIP URI
	(sip:<username>@phone.plivo.com), not the bare username — confirmed via a
	live test call on 2026-07-29 (CRM Call Log 95d43c62-... recorded
	From="sip:Administrator20063529841669406491173@phone.plivo.com"). Strips
	the sip: scheme and @host suffix so it can be matched against the bare
	plivo_endpoint_username stored on CRM Telephony Agent."""
	if not from_value:
		return None
	value = from_value.removeprefix("sip:")
	return value.split("@")[0]


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
def get_number_capabilities(number: str):
	"""Look up what a Plivo number can actually receive (voice/SMS) — needed
	before pointing a WABA-registration OTP at it, since some Plivo number
	types are voice-only or SMS-only and Meta's OTP can arrive either way."""
	settings = get_plivo_settings()
	auth_id = settings.auth_id
	auth_token = settings.get_password("auth_token")

	response = requests.get(
		f"https://api.plivo.com/v1/Account/{auth_id}/Number/{number}/",
		auth=(auth_id, auth_token),
	)
	response.raise_for_status()
	data = response.json()

	return {
		"number": data.get("number"),
		"voice_enabled": bool(data.get("voice_enabled")),
		"sms_enabled": bool(data.get("sms_enabled")),
		"number_type": data.get("number_type"),
		"region": data.get("region"),
		"application": data.get("application"),
	}


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
