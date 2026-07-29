<template>
  <TwilioCallUI ref="twilio" />
  <ExotelCallUI ref="exotel" />
  <PlivoCallUI ref="plivo" />
  <Dialog
    v-model:open="show"
    :title="__('Make Call')"
    :actions="[
      {
        label: __('Call using {0}', [callMedium]),
        variant: 'solid',
        onClick: makeCallUsing,
      },
    ]"
  >
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="mobileNumber"
          type="text"
          :label="__('Mobile Number')"
        />
        <FormControl
          v-model="callMedium"
          type="select"
          :label="__('Calling Medium')"
          :options="mediumOptions"
        />
        <div class="flex flex-col gap-1">
          <FormControl
            v-model="isDefaultMedium"
            type="checkbox"
            :label="__('Make {0} as default calling medium', [callMedium])"
          />

          <div v-if="isDefaultMedium" class="text-sm text-ink-gray-4">
            {{
              __('You can change the default calling medium from the settings')
            }}
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import TwilioCallUI from '@/components/Telephony/TwilioCallUI.vue'
import ExotelCallUI from '@/components/Telephony/ExotelCallUI.vue'
import PlivoCallUI from '@/components/Telephony/PlivoCallUI.vue'
import { defaultCallingMedium, useTelephony } from '@/composables/telephony'
import { globalStore } from '@/stores/global'
import { FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'

const { setMakeCall } = globalStore()
const { isEnabled, isAnyEnabled } = useTelephony()

const twilio = ref(null)
const exotel = ref(null)
const plivo = ref(null)

const callMedium = ref('Twilio')
const isDefaultMedium = ref(false)

const show = ref(false)
const mobileNumber = ref('')

// Plivo browser calling is a separate opt-in capability on top of the bare
// "plivo" provider-enabled flag (see crm.integrations.api.
// is_call_integration_enabled) — an org can have Plivo enabled for
// server-side calling only, with browser calling off. Fetched once; the
// medium list below only offers "Plivo (Browser)" when this is genuinely on,
// so agents are never shown a choice that would fail immediately.
const plivoBrowserCallingEnabled = ref(false)
createResource({
  url: 'crm.integrations.api.is_call_integration_enabled',
  cache: 'Is Call Integration Enabled',
  auto: true,
  onSuccess: (data) => {
    plivoBrowserCallingEnabled.value = Boolean(data.plivo_browser_calling_enabled)
  },
})

// Plivo genuinely offers TWO distinct calling mechanisms behind one
// "provider enabled" flag — a headset/browser call (PlivoCallUI's WebRTC
// client) and a phone call (Exotel-style: agent's real phone rings first).
// These aren't interchangeable, so both need to be explicit, separately
// selectable options rather than collapsing to whichever the UI picks by
// default — that's what silently hid the phone-call option entirely before.
const enabledIntegrations = computed(() => {
  const options = [
    { key: 'twilio', label: 'Twilio', ref: twilio },
    { key: 'exotel', label: 'Exotel', ref: exotel },
  ].filter(({ key }) => isEnabled(key))

  if (isEnabled('plivo')) {
    if (plivoBrowserCallingEnabled.value) {
      options.push({ key: 'plivo', label: 'Plivo (Browser)', ref: plivo, mode: 'browser' })
    }
    options.push({ key: 'plivo', label: 'Plivo (Phone)', ref: plivo, mode: 'server' })
  }

  return options
})

const mediumOptions = computed(() => enabledIntegrations.value.map((o) => o.label))

function makeCall(number) {
  if (enabledIntegrations.value.length > 1 && !defaultCallingMedium.value) {
    mobileNumber.value = number
    show.value = true
    return
  }

  callMedium.value = enabledIntegrations.value[0]?.label ?? 'Twilio'
  if (defaultCallingMedium.value) {
    callMedium.value = defaultCallingMedium.value
  }

  mobileNumber.value = number
  makeCallUsing()
}

function makeCallUsing() {
  if (isDefaultMedium.value && callMedium.value) {
    setDefaultCallingMedium()
  }

  if (callMedium.value === 'Twilio') {
    twilio.value.makeOutgoingCall(mobileNumber.value)
  }

  if (callMedium.value === 'Exotel') {
    exotel.value.makeOutgoingCall(mobileNumber.value)
  }

  if (callMedium.value === 'Plivo (Browser)') {
    plivo.value.makeOutgoingCall(mobileNumber.value)
  }

  if (callMedium.value === 'Plivo (Phone)') {
    plivo.value.makeServerCall(mobileNumber.value)
  }
  show.value = false
}

async function setDefaultCallingMedium() {
  await call('crm.integrations.api.set_default_calling_medium', {
    medium: callMedium.value,
  })

  defaultCallingMedium.value = callMedium.value
  toast.success(
    __('Default calling medium set successfully to {0}', [callMedium.value]),
  )
}

watch(
  isAnyEnabled,
  () =>
    nextTick(() => {
      for (const {
        key,
        label,
        ref: integrationRef,
      } of enabledIntegrations.value) {
        integrationRef.value.setup()
        callMedium.value = label
      }

      if (isAnyEnabled.value) {
        callMedium.value = enabledIntegrations.value[0]?.label ?? 'Twilio'
        setMakeCall(makeCall)
      }
    }),
  { immediate: true },
)
</script>
