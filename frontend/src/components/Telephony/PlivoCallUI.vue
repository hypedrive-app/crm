<template>
  <div v-show="showCallPopup" v-bind="$attrs">
    <div
      ref="callPopup"
      class="fixed z-20 flex w-60 cursor-move select-none flex-col rounded-lg bg-surface-gray-10 p-4 text-ink-gray-2 shadow-2xl"
      :style="style"
    >
      <div class="flex flex-row-reverse items-center gap-1">
        <MinimizeIcon
          class="h-4 w-4 cursor-pointer"
          @click="toggleCallWindow"
        />
      </div>
      <div class="flex flex-col items-center justify-center gap-3">
        <Avatar
          v-if="contact?.image"
          :image="contact.image"
          :label="contact.full_name"
          class="relative flex !h-24 !w-24 items-center justify-center [&>div]:text-[30px]"
          :class="onCall || calling ? '' : 'pulse'"
        />
        <div class="flex flex-col items-center justify-center gap-1">
          <div class="text-2xl-medium">
            {{ contact?.full_name ?? __('Unknown') }}
          </div>
          <div class="text-sm text-ink-gray-5">{{ contact?.mobile_no }}</div>
        </div>
        <CountUpTimer ref="counterUp">
          <div v-if="onCall" class="my-1 text-base">
            {{ counterUp?.updatedTime }}
          </div>
        </CountUpTimer>
        <div v-if="!onCall" class="my-1 text-base">
          {{ calling ? __('Calling...') : __('Incoming call...') }}
        </div>
        <div v-if="onCall" class="flex gap-2">
          <Button
            :icon="muted ? 'mic-off' : 'mic'"
            class="rounded-full"
            @click="toggleMute"
          />
          <Button
            class="cursor-pointer rounded-full"
            :tooltip="__('Add a Note')"
            :icon="NoteIcon"
            @click="openNoteModal"
          />
          <Button
            class="rounded-full bg-surface-red-7 hover:bg-surface-red-8 rotate-[135deg] text-ink-base"
            :tooltip="__('Hang Up')"
            :icon="PhoneIcon"
            @click="hangUpCall"
          />
        </div>
        <div v-else-if="calling">
          <Button
            size="md"
            variant="solid"
            theme="red"
            :label="__('Cancel')"
            class="rounded-lg text-ink-base"
            @click="cancelCall"
          >
            <template #prefix>
              <PhoneIcon class="rotate-[135deg]" />
            </template>
          </Button>
        </div>
        <div v-else class="flex gap-2">
          <Button
            size="md"
            variant="solid"
            theme="green"
            :label="__('Accept')"
            class="rounded-lg text-ink-base"
            :iconLeft="PhoneIcon"
            @click="acceptIncomingCall"
          />
          <Button
            size="md"
            variant="solid"
            theme="red"
            :label="__('Reject')"
            class="rounded-lg text-ink-base"
            @click="rejectIncomingCall"
          >
            <template #prefix>
              <PhoneIcon class="rotate-[135deg]" />
            </template>
          </Button>
        </div>
      </div>
    </div>
  </div>
  <div
    v-show="showSmallCallWindow"
    class="ml-2 flex cursor-pointer select-none items-center justify-between gap-3 rounded-lg bg-surface-gray-10 px-2 py-[7px] text-base text-ink-gray-2"
    v-bind="$attrs"
    @click="toggleCallWindow"
  >
    <div class="flex items-center gap-2">
      <Avatar
        v-if="contact?.image"
        :image="contact.image"
        :label="contact.full_name"
        class="relative flex !h-5 !w-5 items-center justify-center"
      />
      <div class="max-w-[120px] truncate">
        {{ contact?.full_name ?? __('Unknown') }}
      </div>
    </div>
    <div v-if="onCall" class="flex items-center gap-2">
      <div class="my-1 min-w-[40px] text-center">
        {{ counterUp?.updatedTime }}
      </div>
      <Button
        variant="solid"
        theme="red"
        class="!h-6 !w-6 rounded-full rotate-[135deg] text-ink-base"
        :icon="PhoneIcon"
        @click.stop="hangUpCall"
      />
    </div>
    <div v-else-if="calling" class="flex items-center gap-3">
      <div class="my-1">{{ __('Calling...') }}</div>
      <Button
        variant="solid"
        theme="red"
        class="!h-6 !w-6 rounded-full rotate-[135deg] text-ink-base"
        :icon="PhoneIcon"
        @click.stop="cancelCall"
      />
    </div>
    <div v-else class="flex items-center gap-2">
      <Button
        variant="solid"
        theme="green"
        class="pulse relative !h-6 !w-6 rounded-full animate-pulse text-ink-base"
        :tooltip="__('Accept Call')"
        :icon="PhoneIcon"
        @click.stop="acceptIncomingCall"
      />
      <Button
        variant="solid"
        theme="red"
        class="!h-6 !w-6 rounded-full rotate-[135deg] text-ink-base"
        :tooltip="__('Reject Call')"
        :icon="PhoneIcon"
        @click.stop="rejectIncomingCall"
      />
    </div>
  </div>
</template>

<script setup>
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import MinimizeIcon from '@/components/Icons/MinimizeIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import CountUpTimer from '@/components/CountUpTimer.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'
import Plivo from 'plivo-browser-sdk'
import { useDraggable, useWindowSize } from '@vueuse/core'
import { useTelemetry } from 'frappe-ui/frappe'
import { Avatar, call, createResource, toast } from 'frappe-ui'
import { ref, watch } from 'vue'

const { capture } = useTelemetry()

// plivo-browser-sdk's default export is a thin wrapper class whose
// constructor creates `.client` (an EventEmitter) — the SDK, not us, owns
// the WebSocket/SIP registration lifecycle from there.
let plivoInstance = null
let client = null
let log = ref('Connecting...')
let currentCallUUID = null
// True once the SDK has logged in. `log` is internal diagnostic state that is
// never rendered anywhere, so without this every startup/login failure left the
// call button looking operational while doing nothing at all.
const ready = ref(false)

let showCallPopup = ref(false)
let showSmallCallWindow = ref(false)
let onCall = ref(false)
let calling = ref(false)
let muted = ref(false)
let callPopup = ref(null)
let counterUp = ref(null)

const phoneNumber = ref('')

const contact = ref({
  full_name: '',
  image: '',
  mobile_no: '',
})

watch(phoneNumber, (value) => {
  if (!value) return
  getContact.fetch()
})

const getContact = createResource({
  url: 'crm.integrations.api.get_contact_by_phone_number',
  makeParams() {
    return {
      phone_number: phoneNumber.value,
    }
  },
  cache: ['contact', phoneNumber.value],
  onSuccess(data) {
    contact.value = data
  },
})

const { showModal } = useDoctypeModal()
const note = ref({
  name: '',
  title: '',
  content: '',
})

function openNoteModal() {
  showModal({
    name: note.value.name || null,
    doctype: 'CRM Call Log',
    title: 'Call Log',
    callbacks: {
      afterInsert: (n) => updateNote(n, true),
      afterUpdate: updateNote,
    },
  })
}

async function updateNote(_note, isInsert = false) {
  note.value = _note
  if (isInsert && _note.name && currentCallUUID) {
    await call('crm.integrations.api.add_note_to_call_log', {
      call_sid: currentCallUUID,
      note: _note,
    })
    capture('note_created')
  } else {
    capture('note_updated')
  }
}

const { width, height } = useWindowSize()

let { style } = useDraggable(callPopup, {
  initialValue: { x: width.value - 280, y: height.value - 310 },
  preventDefault: true,
})

async function startupClient() {
  // Plivo can be enabled purely for server-side (Exotel-style) calling with
  // browser calling left off — get_browser_calling_credentials throws in
  // that case (by design, see crm.integrations.plivo.handler), so this needs
  // to check first rather than surface that as a startup error to every
  // Plivo user, only those who've actually turned browser calling on.
  const { plivo_browser_calling_enabled } = await call(
    'crm.integrations.api.is_call_integration_enabled',
  )
  if (!plivo_browser_calling_enabled) return

  log.value = 'Requesting Endpoint credentials...'

  try {
    const data = await call('crm.integrations.plivo.handler.get_browser_calling_credentials')
    log.value = 'Got Endpoint credentials.'
    initializeClient(data.username, data.password)
  } catch (err) {
    log.value = 'An error occurred. ' + err.message
    // `log` is internal diagnostic state that is never rendered, so a failure
    // here used to leave the agent with a call button that silently does
    // nothing. Surface it.
    ready.value = false
    toast.error(
      __('Could not start browser calling: {0}', [err.message || __('unknown error')]),
    )
  }
}

function initializeClient(username, password) {
  plivoInstance = new Plivo({
    debug: 'ERROR',
    permOnClick: true,
  })
  client = plivoInstance.client

  addClientListeners()

  client.login(username, password)
}

function addClientListeners() {
  client.on('onLogin', () => {
    log.value = 'Ready to make and receive calls!'
    ready.value = true
  })

  client.on('onLoginFailed', (cause) => {
    log.value = 'Plivo login failed: ' + cause
    ready.value = false
    toast.error(
      __('Browser calling could not sign in to Plivo: {0}', [
        cause || __('unknown reason'),
      ]),
    )
  })

  // WebRTC unsupported / no media permission. Plivo emits these instead of
  // failing the call outright, and both were previously swallowed into `log`,
  // which is why a blocked microphone produced a call that never connected and
  // never explained itself.
  client.on('onWebrtcNotSupported', () => {
    log.value = 'WebRTC not supported'
    ready.value = false
    toast.error(
      __('This browser cannot place calls. Use Chrome, Edge or Safari over HTTPS.'),
    )
  })

  client.on('onMediaPermission', (evt) => {
    // Shape varies by SDK version; treat anything non-granted as a denial.
    const denied =
      evt === false ||
      evt?.error ||
      (evt?.status && String(evt.status).toLowerCase() !== 'granted')
    if (!denied) return
    log.value = 'Microphone permission denied'
    toast.error(
      __(
        'Microphone access is blocked, so the call has no audio. Allow the microphone for this site in your browser settings, then try again.',
      ),
    )
  })

  client.on('onCalling', () => {
    log.value = 'Calling...'
    calling.value = true
    showCallPopup.value = true
  })

  client.on('onCallRemoteRinging', () => {
    log.value = 'Ringing...'
  })

  client.on('onCallAnswered', (callInfo) => {
    log.value = 'Call answered.'
    currentCallUUID = callInfo?.callUUID || client.getCallUUID()
    calling.value = false
    onCall.value = true
    counterUp.value.start()
    capture('make_outgoing_call')
  })

  client.on('onCallTerminated', () => {
    log.value = 'Call ended.'
    resetCallState()
  })

  client.on('onCallFailed', (causeCode) => {
    log.value = 'Call failed: ' + causeCode
    toast.error(__('Call failed: {0}', [causeCode || __('unknown reason')]))
    resetCallState()
  })

  client.on('onIncomingCall', (callerId) => {
    log.value = `Incoming call from ${callerId}`
    phoneNumber.value = callerId
    currentCallUUID = client.getCallUUID()
    showCallPopup.value = true
    calling.value = false
    onCall.value = false
  })
}

function resetCallState() {
  calling.value = false
  onCall.value = false
  showCallPopup.value = false
  showSmallCallWindow.value = false
  muted.value = false
  currentCallUUID = null
  counterUp.value?.stop()
  note.value = {
    name: '',
    title: '',
    content: '',
  }
}

function toggleMute() {
  if (muted.value) {
    client.unmute()
    muted.value = false
  } else {
    client.mute()
    muted.value = true
  }
}

function acceptIncomingCall() {
  log.value = 'Accepted incoming call.'
  onCall.value = true
  client.answer(currentCallUUID)
  counterUp.value.start()
}

function rejectIncomingCall() {
  client.reject(currentCallUUID)
  log.value = 'Rejected incoming call'
  resetCallState()
}

function hangUpCall() {
  client.hangup()
  log.value = 'Hanging up call'
  resetCallState()
}

function cancelCall() {
  client.hangup()
  resetCallState()
}

function makeOutgoingCall(number) {
  phoneNumber.value = number

  if (!number) {
    toast.error(__('This record has no phone number to call.'))
    return
  }

  if (!client || !client.isRegistered()) {
    log.value = 'Client not registered yet.'
    // This early return is why the call button appeared to do nothing: the
    // caller got no feedback whatsoever, so a not-yet-registered (or
    // failed-to-register) client was indistinguishable from a broken button.
    toast.error(
      __(
        'Browser calling is still connecting. Wait a moment and try again — if it keeps failing, check Plivo settings.',
      ),
    )
    startupClient()
    return
  }

  log.value = `Attempting to call ${number} ...`
  client.call(number, {})
}

// Server-side (Exotel-style) calling: rings the agent's own real phone first
// via crm.integrations.plivo.handler.make_a_call, then bridges to the
// destination — no browser SDK / headset involved at all, a completely
// separate code path from makeOutgoingCall above. Exposed as a distinct
// method (not a mode flag on makeOutgoingCall) since CallUI.vue needs to
// offer both as explicit choices for the same "Plivo" provider.
async function makeServerCall(number) {
  try {
    await call('crm.integrations.plivo.handler.make_a_call', { to_number: number })
    toast.success(__('Calling your phone — answer it to connect to {0}', [number]))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Failed to place call'))
  }
}

function toggleCallWindow() {
  showCallPopup.value = !showCallPopup.value
  showSmallCallWindow.value = !showSmallCallWindow.value
}

watch(
  () => log.value,
  (value) => {
    console.log(value)
  },
  { immediate: true },
)

defineExpose({ makeOutgoingCall, makeServerCall, setup: startupClient })
</script>

<style scoped>
.pulse::before {
  content: '';
  position: absolute;
  border: 1px solid green;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  border-radius: 50%;
  animation: pulse 1s linear infinite;
}

.pulse::after {
  content: '';
  position: absolute;
  border: 1px solid green;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  border-radius: 50%;
  animation: pulse 1s linear infinite;
  animation-delay: 0.3s;
}

@keyframes pulse {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }

  50% {
    transform: scale(1);
    opacity: 1;
  }

  100% {
    transform: scale(1.3);
    opacity: 0;
  }
}
</style>
