<template>
  <div
    v-if="conversationId && !canReply"
    class="flex flex-col gap-2 px-3 py-2.5 sm:px-10 text-p-sm text-ink-gray-5"
  >
    <div class="flex items-start gap-2 sm:items-center">
      <span
        class="lucide-clock mt-0.5 size-4 shrink-0 text-ink-gray-4 sm:mt-0"
        aria-hidden="true"
      />
      <span class="flex-1">
        {{
          __(
            "This conversation is outside the reply window (common on WhatsApp after 24 hours of inactivity). The customer needs to message first, or send a template message to reopen it.",
          )
        }}
      </span>
    </div>
    <!-- Both actions stay reachable here. Previously this branch offered only
         "Send Template", so Canned Responses became unreachable the moment a
         conversation fell outside the reply window — even though a canned
         response is just text that can be pasted into a template's parameters,
         and agents rely on that copy. Buttons wrap on mobile rather than
         squeezing the message text. -->
    <div class="flex flex-wrap items-center gap-2 self-end">
      <Button variant="subtle" @click="showCannedResponses = true">
        {{ __('Canned Responses') }}
      </Button>
      <Button variant="solid" @click="showTemplates = true">
        {{ __('Send Template') }}
      </Button>
    </div>
  </div>
  <div v-else class="flex items-end gap-2 px-3 py-2.5 sm:px-10" v-bind="$attrs">
    <div class="flex h-8 shrink-0 items-center gap-1">
      <Tooltip :text="__('Canned Responses')">
        <button
          type="button"
          :aria-label="__('Canned Responses')"
          :disabled="!conversationId"
          class="flex size-7 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-7 disabled:pointer-events-none disabled:opacity-40"
          @click="showCannedResponses = true"
        >
          <ChatwootIcon class="size-4.5" />
        </button>
      </Tooltip>
      <Tooltip :text="__('Send Template')">
        <button
          type="button"
          :aria-label="__('Send Template')"
          :disabled="!conversationId"
          class="flex size-7 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-7 disabled:pointer-events-none disabled:opacity-40"
          @click="showTemplates = true"
        >
          <span class="lucide-file-text size-4.5" aria-hidden="true" />
        </button>
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
      :disabled="!conversationId || !content.trim()"
      @click="sendTextMessage()"
    >
      {{ __('Send') }}
    </Button>
  </div>
  <ChatwootCannedResponseModal
    v-model="showCannedResponses"
    @send="useCannedResponse"
  />
  <ChatwootTemplateSelectorModal
    ref="templateModalRef"
    v-model="showTemplates"
    @send="sendTemplateMessage"
  />
</template>

<script setup>
import ChatwootIcon from '@/components/Icons/ChatwootIcon.vue'
import ChatwootCannedResponseModal from '@/components/Modals/ChatwootCannedResponseModal.vue'
import ChatwootTemplateSelectorModal from '@/components/Modals/ChatwootTemplateSelectorModal.vue'
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
const showTemplates = ref(false)
const templateModalRef = ref(null)

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
  // Belt-and-braces: the composer is normally swapped out when `canReply` is
  // false, but Enter can still fire from a stale render, and a free-form send in
  // that state is guaranteed to be rejected by Meta. Fail loudly and keep the
  // text rather than posting a message that silently ends up `failed`.
  if (!props.canReply) {
    toast.error(
      __('Outside the 24h reply window — send a template message instead.'),
    )
    return
  }
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
    onSuccess: (data) => {
      capture('chatwoot_send_message')
      chatwoot.value?.reload?.()
      // A 200 here only means Chatwoot ACCEPTED the message, not that WhatsApp
      // delivered it. Meta rejects out-of-window sends asynchronously, so the
      // message lands in the thread and then flips to status 'failed' a moment
      // later — verified live on a reply-locked conversation. Without this the
      // agent believes a message went out that never will.
      if (String(data?.status || '').toLowerCase() === 'failed') {
        content.value = messageContent
        toast.error(
          __(
            'WhatsApp rejected this message — the 24h reply window has closed. Send a template instead.',
          ),
        )
      }
    },
    onError: (error) => {
      content.value = messageContent
      toast.error(error.messages?.[0] || __('Failed to send message'))
    },
  })
}

function sendTemplateMessage({ templateName, category, language, processedParams }) {
  if (!props.conversationId) return
  templateModalRef.value?.setSending(true)
  createResource({
    url: 'crm.api.chatwoot.send_chatwoot_template',
    params: {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      conversation_id: props.conversationId,
      template_name: templateName,
      category,
      language,
      processed_params: processedParams,
    },
    auto: true,
    onError: (error) => {
      templateModalRef.value?.setSending(false)
      // Only dismiss the dialog once the send is confirmed to have gone
      // through — closing unconditionally hides genuine failures (e.g.
      // Chatwoot/Meta rejecting the template) behind a dialog that appeared
      // to close as if the send had succeeded.
      templateModalRef.value?.setError(
        error.messages?.[0] || __('Failed to send template message'),
      )
      toast.error(error.messages?.[0] || __('Failed to send template message'))
    },
    onSuccess: () => {
      capture('chatwoot_send_template')
      templateModalRef.value?.setSending(false)
      templateModalRef.value?.closeAfterSuccess()
      chatwoot.value?.reload?.()
    },
  })
}

defineExpose({ show })
</script>
