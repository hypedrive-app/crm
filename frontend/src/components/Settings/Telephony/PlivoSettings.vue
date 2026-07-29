<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex gap-1 items-center">
        <Button
          variant="ghost"
          icon-left="lucide-chevron-left"
          :label="__('Plivo Settings')"
          size="md"
          class="cursor-pointer -ml-4 hover:bg-transparent focus:bg-transparent focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:none active:bg-transparent active:outline-none active:ring-0 active:ring-offset-0 active:text-ink-gray-5 text-2xl-semibold hover:opacity-70 !pr-0 !max-w-96 !justify-start"
          @click="emit('updateStep', 'telephony-settings')"
        />
        <Badge
          v-if="plivo.doc?.enabled && isDirty"
          :label="__('Not Saved')"
          variant="subtle"
          theme="orange"
        />
      </div>
    </template>
    <template #header-actions>
      <div v-if="plivo.doc?.enabled && !plivo.get.loading" class="flex gap-2">
        <Button
          v-if="isDirty"
          :label="__('Discard Changes')"
          variant="subtle"
          @click="plivo.reload()"
        />
        <Button :label="__('Disable')" variant="subtle" @click="disable" />
        <Button
          variant="solid"
          :label="__('Update')"
          :loading="plivo.save.loading"
          :disabled="!isDirty"
          @click="update"
        />
      </div>
    </template>
    <template #content>
      <div v-if="plivo.doc" class="h-full">
        <div v-if="plivo.doc.enabled" class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormControl
              v-model="plivo.doc.auth_id"
              :label="__('Auth ID')"
              type="text"
              placeholder="MAXXXXXXXXXXXXXXXXXXXX"
              required
              autocomplete="off"
            />
            <Password
              v-model="plivo.doc.auth_token"
              :label="__('Auth Token')"
              placeholder="************"
              required
            />
            <FormControl
              v-model="plivo.doc.webhook_verify_token"
              :label="__('Webhook Verify Token')"
              type="text"
              placeholder="my_secure_token_123"
              required
              autocomplete="off"
            />
          </div>
          <div class="h-px border-t border-outline-elevation-2" />
          <div class="flex items-center justify-between">
            <div class="flex flex-col">
              <div class="text-p-base-medium text-ink-gray-7 truncate">
                {{ __('Record Calls') }}
              </div>
              <div class="text-p-sm text-ink-gray-5 truncate">
                {{ __('Enable call recording for outgoing calls') }}
              </div>
            </div>
            <div>
              <Switch v-model="plivo.doc.record_call" size="sm" />
            </div>
          </div>
          <div class="h-px border-t border-outline-elevation-2" />
          <div class="flex items-center justify-between">
            <div class="flex flex-col">
              <div class="text-p-base-medium text-ink-gray-7 truncate">
                {{ __('Browser Calling') }}
              </div>
              <div class="text-p-sm text-ink-gray-5 truncate">
                {{
                  __(
                    'Let agents call from their headset in the browser tab, instead of ringing their real phone',
                  )
                }}
              </div>
            </div>
            <div>
              <Switch v-model="plivo.doc.browser_calling_enabled" size="sm" />
            </div>
          </div>
          <div v-if="plivo.doc.browser_calling_enabled" class="space-y-4">
            <div class="rounded-lg bg-surface-amber-1 border border-outline-amber-2 p-3 text-p-sm text-ink-gray-7">
              {{
                __(
                  "Browser calling needs a stable outbound connection: agents on a restrictive office/corporate firewall may need UDP traffic to Plivo's SIP signalling and media servers explicitly allowed, or calls may fail to connect even though login succeeds.",
                )
              }}
            </div>
            <FormControl
              v-model="plivo.doc.application_id"
              :label="__('Application ID')"
              type="text"
              placeholder="27579xxxxxxxxxxx"
              required
              autocomplete="off"
              :description="
                __(
                  'A Plivo Application whose Answer URL and Hangup URL both point at this site (same webhook endpoints as above).',
                )
              "
            />
          </div>
        </div>
        <!--  Disabled state -->
        <div v-else class="relative flex h-full w-full justify-center">
          <div
            class="absolute left-1/2 flex w-64 -translate-x-1/2 flex-col items-center gap-3"
            :style="{ top: '35%' }"
          >
            <div class="flex flex-col items-center gap-1.5 text-center">
              <PhoneIcon class="size-7.5 text-ink-gray-7" />
              <span class="text-lg-medium text-ink-gray-8">
                {{ __('Plivo Integration Disabled') }}
              </span>
              <span class="text-center text-p-base text-ink-gray-6">
                {{
                  __(
                    'Enable Plivo integration to make calls directly from your CRM',
                  )
                }}
              </span>
              <Button :label="__('Enable')" variant="solid" @click="enable" />
            </div>
          </div>
        </div>
      </div>
      <div
        v-else-if="plivo.get.loading"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
    </template>
  </SettingsLayoutBase>
</template>
<script setup>
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import { setEnabled } from '@/composables/telephony'
import { useDocument } from '@/data/document'
import { Switch } from 'frappe-ui'
import { computed } from 'vue'

const emit = defineEmits(['updateStep'])

const { document: plivo } = useDocument('CRM Plivo Settings', 'CRM Plivo Settings')

function enable() {
  plivo.doc.enabled = true
}

function disable() {
  plivo.doc.enabled = false
  update()
}

function update() {
  plivo.save.submit(null, {
    onSuccess: () => plivo.reload(),
  })

  setEnabled('plivo', plivo.doc.enabled)
}

const isDirty = computed(() => {
  return (
    plivo.doc &&
    plivo.originalDoc &&
    JSON.stringify(plivo.doc) !== JSON.stringify(plivo.originalDoc)
  )
})
</script>
