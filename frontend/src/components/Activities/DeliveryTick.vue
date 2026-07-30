<template>
  <Tooltip v-if="state.label" :text="state.label">
    <span :class="[state.icon, state.class]" aria-hidden="true" />
    <span class="sr-only">{{ state.label }}</span>
  </Tooltip>
</template>

<script setup>
import { Tooltip } from 'frappe-ui'
import { computed } from 'vue'

// Delivery state for an outgoing message, shared by the Chatwoot and WhatsApp
// threads so a tick means exactly the same thing on both surfaces.
//
// Visual ladder mirrors WhatsApp's own semantics:
//   clock (queued/sending) -> single check (sent) -> double grey (delivered)
//   -> double blue (read) -> red alert (failed)
//
// The two backends report status in different vocabularies and neither is a
// closed enum: Chatwoot emits lowercase Rails states, while the WhatsApp
// doctype's `status` field is free-text Data mixing app-level values
// ('Success', 'Failed', 'marked as read') with Meta's own webhook strings
// ('sent', 'delivered', 'read'). Both are normalised here — case-insensitively
// — so neither call site has to carry its own lookup table.
const props = defineProps({
  status: { type: String, default: '' },
})

const READ = ['read', 'marked as read']
const DELIVERED = ['delivered']
const SENT = ['sent', 'success']
const FAILED = ['failed', 'failure', 'error']

const state = computed(() => {
  const status = (props.status || '').trim().toLowerCase()

  if (FAILED.includes(status)) {
    return {
      icon: 'lucide-alert-circle',
      class: 'size-3.5 text-ink-red-3',
      label: __('Failed to send'),
    }
  }
  if (READ.includes(status)) {
    return {
      icon: 'lucide-check-check',
      class: 'size-3.5 text-ink-blue-4',
      label: __('Read'),
    }
  }
  if (DELIVERED.includes(status)) {
    return {
      icon: 'lucide-check-check',
      class: 'size-3.5 text-ink-gray-5',
      label: __('Delivered'),
    }
  }
  if (SENT.includes(status)) {
    return {
      icon: 'lucide-check',
      class: 'size-3.5 text-ink-gray-5',
      label: __('Sent'),
    }
  }
  // No status yet — a local echo that has not been acknowledged.
  return {
    icon: 'lucide-clock',
    class: 'size-3 text-ink-gray-4',
    label: __('Sending'),
  }
})
</script>
