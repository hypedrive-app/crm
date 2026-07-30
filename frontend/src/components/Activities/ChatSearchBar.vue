<template>
  <!-- No horizontal padding here: both callers (WhatsAppArea, ChatwootArea)
       mount this inside a wrapper already padded `px-3 sm:px-10`, so padding
       here double-indented the search field past the message column. The Area
       wrapper is the single source of horizontal padding. -->
  <div class="mb-3">
    <TextInput
      ref="inputRef"
      v-model="query"
      :placeholder="__('Search in this chat')"
      class="w-full"
      @keydown.esc="$emit('escape')"
    >
      <template #prefix>
        <span
          class="lucide-search size-4 text-ink-gray-6"
          aria-hidden="true"
        />
      </template>
      <template v-if="query" #suffix>
        <span
          class="lucide-x size-4 cursor-pointer text-ink-gray-5 hover:text-ink-gray-7"
          aria-hidden="true"
          @click="$emit('clear')"
        />
      </template>
    </TextInput>
    <div
      v-if="query && !resultCount"
      class="mt-3 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('No messages found for "{0}"', [query]) }}
    </div>
  </div>
</template>

<script setup>
import { TextInput } from 'frappe-ui'
import { computed, ref } from 'vue'

// The search field for a conversation thread. Presentation only — the query
// state, filtering and escape-ladder all live in useMessageSearch so both the
// Chatwoot and WhatsApp threads share one behaviour.
defineProps({
  resultCount: { type: Number, default: 0 },
})

defineEmits(['clear', 'escape'])

const query = defineModel({ type: String, default: '' })

// Forwarded so useMessageSearch's `searchInputRef.value.el.focus()` reaches the
// real <input> through this wrapper. Mirrors frappe-ui TextInput's own
// `defineExpose({ el: inputRef })` shape so this component is drop-in
// interchangeable with a bare TextInput at the call site: `el` resolves to the
// child component instance, whose own exposed `el` is the DOM node.
const inputRef = ref(null)
const el = computed(() => inputRef.value?.el)
defineExpose({ el })
</script>
