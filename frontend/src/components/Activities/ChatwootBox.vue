<template>
  <div class="flex items-end gap-2 px-3 py-2.5 sm:px-10" v-bind="$attrs">
    <Textarea
      ref="textareaRef"
      v-model="content"
      type="textarea"
      class="min-h-8 w-full"
      :rows="rows"
      :placeholder="placeholder"
      :disabled="!conversationId"
      @focus="rows = 4"
      @blur="rows = 1"
      @keydown="onKeydown"
      @compositionstart="isComposing = true"
      @compositionend="isComposing = false"
    />
    <Button
      variant="solid"
      :disabled="!conversationId || !content"
      @click="sendTextMessage()"
    >
      {{ __('Send') }}
    </Button>
  </div>
</template>

<script setup>
import { useTelemetry } from 'frappe-ui/frappe'
import { Textarea, Button, createResource, toast } from 'frappe-ui'
import { ref, nextTick } from 'vue'

const props = defineProps({
  conversationId: { type: [Number, String], default: null },
})

const chatwoot = defineModel('chatwoot', { type: Object, default: () => ({}) })

const { capture } = useTelemetry()

const rows = ref(1)
const textareaRef = ref(null)
const content = ref('')
const placeholder = ref(__('Type your message here...'))

// IME composition guard: while an IME (Hindi/Japanese/Chinese input, or an
// emoji-picker candidate list) is composing, the Enter keystroke that
// commits the candidate fires as a normal 'Enter' keydown too. Treating that
// as "send" swallows the user's composed text and sends garbage/nothing —
// so BOTH the browser's own `event.isComposing` and the legacy keyCode 229
// fallback (older Safari/some Android WebViews don't set isComposing
// reliably) are checked before Enter is ever treated as submit.
const isComposing = ref(false)

function isComposingEvent(event) {
  return isComposing.value || event.isComposing || event.keyCode === 229
}

function onKeydown(event) {
  if (event.key !== 'Enter') return
  if (isComposingEvent(event)) return
  if (event.shiftKey) return // Shift+Enter = newline, never sends
  event.preventDefault()
  sendTextMessage()
}

function show() {
  nextTick(() => textareaRef.value?.el?.focus())
}

function sendTextMessage() {
  if (!props.conversationId || !content.value.trim()) return
  sendChatwootMessage()
  textareaRef.value?.el?.blur()
}

function sendChatwootMessage() {
  const messageContent = content.value
  content.value = ''
  createResource({
    url: 'crm.api.chatwoot.send_chatwoot_message',
    params: {
      conversation_id: props.conversationId,
      content: messageContent,
    },
    auto: true,
    onSuccess: () => {
      capture('chatwoot_send_message')
      chatwoot.value?.reload?.()
    },
    onError: (error) => {
      content.value = messageContent
      toast.error(error.messages?.[0] || __('Failed to send message'))
    },
  })
}

defineExpose({ show })
</script>
