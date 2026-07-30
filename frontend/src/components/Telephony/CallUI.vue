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
        onClick: confirmCall,
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
// Guards the race that sent browser calls down the SERVER path: this flag
// starts false and only flips true once the resource resolves. If a call is
// placed before then, `enabledIntegrations` omits "Plivo (Browser)" entirely,
// so the stored "Plivo (Browser)" default no longer matches any option and the
// routing falls through to enabledIntegrations[0] === "Plivo (Phone)" — i.e. a
// server call the agent never asked for. `mediumConfigLoaded` lets makeCall
// wait for the real config instead of routing on the default-false placeholder.
const mediumConfigLoaded = ref(false)
const applyMediumConfig = (data) => {
  if (!data) return
  plivoBrowserCallingEnabled.value = Boolean(data.plivo_browser_calling_enabled)
  mediumConfigLoaded.value = true
}
const callConfigResource = createResource({
  url: 'crm.integrations.api.is_call_integration_enabled',
  // NOTE: deliberately NOT sharing telephony.js's 'Is Call Integration Enabled'
  // cache key. When both resources share it, this one gets served from cache
  // and its onSuccess never fires — so mediumConfigLoaded stayed false forever,
  // waitForMediumConfig() below awaited a promise that never resolved, and the
  // call button silently did nothing. onData fires on cache hits too; the
  // separate key + reading .data (below) are belt-and-braces.
  cache: 'Call Medium Config',
  auto: true,
  onData: applyMediumConfig,
  onSuccess: applyMediumConfig,
})
// If the resource already has data synchronously (cache warm from a prior
// mount), apply it now so the very first click isn't gated on a callback.
if (callConfigResource.data) applyMediumConfig(callConfigResource.data)

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

// Resolves once the calling config has loaded. Routing depends on
// `plivoBrowserCallingEnabled`, which is `false` until its resource resolves,
// so any call placed during that window must wait — otherwise the medium list
// is computed off the placeholder and routes wrong (see mediumConfigLoaded).
function waitForMediumConfig() {
  if (mediumConfigLoaded.value) return Promise.resolve()
  // Kick a fetch in case the resource never auto-loaded, and never wait
  // forever: a 4s cap means a click can't be silently swallowed even if the
  // config request hangs — it falls through to routing on whatever is known,
  // which is strictly better than a dead button.
  callConfigResource.fetch?.()
  return new Promise((resolve) => {
    let settled = false
    const done = () => {
      if (settled) return
      settled = true
      stop()
      clearTimeout(timer)
      resolve()
    }
    const stop = watch(mediumConfigLoaded, (loaded) => {
      if (loaded) done()
    })
    const timer = setTimeout(done, 4000)
  })
}

async function makeCall(number) {
  if (!number) {
    toast.error(__('Please set a mobile number to make calls'))
    return
  }

  await waitForMediumConfig()

  const options = enabledIntegrations.value
  if (!options.length) {
    toast.error(__('No calling integration is enabled.'))
    return
  }

  // The agent chooses HOW to call. When more than one mechanism is available
  // (e.g. Plivo Browser vs Plivo Phone) always open the picker so a headset
  // call is never silently placed as a phone call, or vice versa. A stored
  // default only pre-selects the dropdown; it does not skip the choice.
  // A single option needs no picker — there is nothing to choose.
  mobileNumber.value = number

  if (options.length === 1) {
    callMedium.value = options[0].label
    dispatchCall(options[0])
    return
  }

  const storedDefault = options.find((o) => o.label === defaultCallingMedium.value)
  callMedium.value = (storedDefault ?? options[0]).label
  show.value = true
}

// Invoked by the picker's "Call using X" button. Maps the currently selected
// label back to its medium object and dispatches — the selection is the
// agent's explicit choice.
function confirmCall() {
  const medium = enabledIntegrations.value.find((o) => o.label === callMedium.value)
  if (!medium) {
    toast.error(__('Please choose a calling medium.'))
    return
  }
  dispatchCall(medium)
}

// Dispatches to the chosen provider. Takes the resolved medium object so the
// label→mechanism mapping lives in one place (enabledIntegrations) instead of
// being re-derived from a string here. Guards against a provider component ref
// that has not mounted yet rather than throwing on `.value.method`.
function dispatchCall(medium) {
  if (isDefaultMedium.value && callMedium.value) {
    setDefaultCallingMedium()
  }

  const providerRef = medium.ref?.value
  if (!providerRef) {
    toast.error(__('Calling is still starting up — try again in a moment.'))
    return
  }

  if (medium.key === 'plivo') {
    // The two Plivo modes are genuinely different mechanisms behind one
    // provider: `browser` places a WebRTC call from this tab (headset),
    // `server` rings the agent's own phone first and bridges.
    if (medium.mode === 'server') {
      providerRef.makeServerCall(mobileNumber.value)
    } else {
      providerRef.makeOutgoingCall(mobileNumber.value)
    }
  } else {
    // Twilio / Exotel expose a single outgoing-call method.
    providerRef.makeOutgoingCall(mobileNumber.value)
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
      // Plivo's browser and phone modes share one component ref, so calling
      // .setup() once per enabledIntegrations entry would log the same
      // WebRTC client in twice — dedupe by ref instead.
      const setupRefs = new Set()
      for (const { label, ref: integrationRef } of enabledIntegrations.value) {
        if (!setupRefs.has(integrationRef)) {
          setupRefs.add(integrationRef)
          integrationRef.value.setup()
        }
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
