<!--
  Renders a WhatsApp Flow message bubble: either the outgoing "here's a form,
  fill it out" prompt (content_type='flow', no flow_response) or the incoming
  filled-out response (content_type='flow', flow_response populated by
  frappe_whatsapp's webhook handler on nfm_reply).
-->
<template>
  <div class="flex flex-col gap-2">
    <div v-if="whatsapp.type == 'Outgoing'" class="flex items-center gap-2">
      <span
        class="lucide-list-checks size-4 shrink-0 text-ink-gray-5"
        aria-hidden="true"
      />
      <div class="flex flex-col gap-0.5">
        <div class="text-p-sm text-ink-gray-6">
          {{ whatsapp.message || __('Please fill out the form') }}
        </div>
        <div class="text-p-sm-medium text-ink-gray-8">
          {{ whatsapp.flow_name || whatsapp.flow }}
        </div>
      </div>
    </div>
    <div v-else-if="answers.length" class="flex flex-col gap-1.5">
      <div class="text-p-sm-medium text-ink-gray-7">
        {{ __('Flow response') }}
      </div>
      <div
        v-for="answer in answers"
        :key="answer.key"
        class="flex flex-col gap-0.5 border-l-2 border-outline-gray-2 pl-2"
      >
        <div class="text-xs text-ink-gray-5">{{ answer.key }}</div>
        <div class="text-p-sm text-ink-gray-8 break-words">{{ answer.value }}</div>
      </div>
    </div>
    <div v-else v-html="formatMessage(whatsapp.message)" />
  </div>
</template>

<script setup>
import { sanitizeHTML } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
  whatsapp: { type: Object, required: true },
})

// flow_response is normalized server-side (crm.api.whatsapp.get_whatsapp_messages)
// from the raw JSON string frappe_whatsapp's webhook stores, into a plain object.
const answers = computed(() => {
  const response = props.whatsapp.flow_response
  if (!response || typeof response !== 'object') return []
  return Object.entries(response)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => ({
      key: humanizeKey(key),
      value: Array.isArray(value) ? value.join(', ') : String(value),
    }))
})

function humanizeKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatMessage(message) {
  return sanitizeHTML(message || '')
}
</script>
