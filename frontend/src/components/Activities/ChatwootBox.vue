<template>
  <div
    v-if="conversationId && !canReply"
    class="flex items-center gap-2 px-3 py-2.5 sm:px-10 text-p-sm text-ink-gray-5"
  >
    <span
      class="lucide-clock size-4 shrink-0 text-ink-gray-4"
      aria-hidden="true"
    />
    {{
      __(
        "This conversation is outside the reply window (common on WhatsApp after 24 hours of inactivity). The customer needs to message first, or send a template message to reopen it.",
      )
    }}
  </div>
  <div v-else class="flex items-end gap-2 px-3 py-2.5 sm:px-10" v-bind="$attrs">
    <div class="flex h-8 shrink-0 items-center gap-2">
      <Tooltip :text="__('Canned Responses')">
        <ChatwootIcon
          class="size-4.5 cursor-pointer text-ink-gray-5 hover:text-ink-gray-7"
          :class="{ 'pointer-events-none opacity-40': !conversationId }"
          @click="showCannedResponses = true"
        />
      </Tooltip>
    </div>
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
      class="shrink-0"
      :disabled="!conversationId || !content"
      @click="sendTextMessage()"
    >
      {{ __('Send') }}
    </Button>
  </div>
  <ChatwootCannedResponseModal
    v-model="showCannedResponses"
    @send="useCannedResponse"
  />
</template>

<script setup>
import ChatwootIcon from '@/components/Icons/ChatwootIcon.vue'
import ChatwootCannedResponseModal from '@/components/Modals/ChatwootCannedResponseModal.vue'
import { useTelemetry } from 'frappe-ui/frappe'
import { Textarea, Button, Tooltip, createResource, toast } from 'frappe-ui'
import { ref, nextTick } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  conversationId: { type: [Number, String], default: null },
  canReply: { type: Boolean, default: true },
})

const chatwoot = defineModel('chatwoot', { type: Object, default: () => ({}) })

const { capture } = useTelemetry()

const rows = ref(1)
const textareaRef = ref(null)
const content = ref('')
const placeholder = ref(__('Type your message here...'))
const showCannedResponses = ref(false)

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

function useCannedResponse(text) {
  content.value = content.value ? `${content.value}\n${text}` : text
  showCannedResponses.value = false
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
      reference_doctype: props.doctype,
      reference_name: props.docname,
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
