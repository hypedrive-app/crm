<template>
  <Dialog v-model:open="show" :title="__('Send WhatsApp Flow')" :size="'lg'">
    <template #default>
      <div
        v-if="flowsResource.loading && !flowsResource.data"
        class="flex h-40 items-center justify-center"
      >
        <LoadingIndicator class="size-6" />
      </div>
      <div
        v-else-if="!flows.length"
        class="flex h-40 flex-col items-center justify-center gap-2 text-center"
      >
        <div class="text-base text-ink-gray-6">
          {{ __('No published WhatsApp Flows available.') }}
        </div>
        <div class="text-p-sm text-ink-gray-5">
          {{
            __(
              'Create and publish a flow from Frappe Desk (WhatsApp Flow) to send it here.',
            )
          }}
        </div>
      </div>
      <div v-else class="flex flex-col gap-2">
<!-- border-outline-gray-2 so the row border is theme-aware in dark mode. -->
        <div
          v-for="flow in flows"
          :key="flow.name"
          class="flex items-center justify-between gap-3 rounded-lg border border-outline-gray-2 p-3"
        >
          <div class="flex min-w-0 flex-col gap-1">
            <div class="flex items-center gap-2">
              <div class="truncate text-p-base-medium text-ink-gray-8">
                {{ flow.flow_name }}
              </div>
              <Badge v-if="flow.category" :label="flow.category" theme="gray" variant="subtle" />
            </div>
            <div v-if="flow.description" class="truncate text-p-sm text-ink-gray-5">
              {{ flow.description }}
            </div>
            <div v-if="flow.screens?.length" class="text-xs text-ink-gray-4">
              {{
                __('{0} screen(s): {1}', [
                  flow.screens.length,
                  flow.screens.map((s) => s.screen_title || s.screen_id).join(', '),
                ])
              }}
            </div>
          </div>
          <Button
            :label="__('Send')"
            variant="solid"
            :loading="sending && sendingFlow === flow.name"
            @click="() => emit('send-flow', flow)"
          />
        </div>
      </div>
      <ErrorMessage class="mt-3" :message="errorMessage" />
    </template>
  </Dialog>
</template>

<script setup>
import { Badge, LoadingIndicator, createResource, ErrorMessage, toast } from 'frappe-ui'
import { computed, watch } from 'vue'

defineProps({
  sending: { type: Boolean, default: false },
  sendingFlow: { type: String, default: '' },
  errorMessage: { type: String, default: '' },
})

const show = defineModel({ type: Boolean })

const emit = defineEmits(['send-flow'])

const flowsResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_flows',
  cache: 'CRM WhatsApp Flows',
  auto: false,
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to load WhatsApp Flows'))
  },
})

const flows = computed(() => flowsResource.data || [])

watch(show, (value) => {
  if (value) {
    flowsResource.reload()
  }
})

defineExpose({ flowsResource })
</script>
