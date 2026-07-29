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
      @keydown.enter.stop="(e) => sendTextMessage(e)"
    />
    <Button variant="solid" :disabled="!conversationId || !content" @click="sendTextMessage()">
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

const whatsapp = defineModel('chatwoot', { type: Object, default: () => ({}) })

const { capture } = useTelemetry()

const rows = ref(1)
const textareaRef = ref(null)
const content = ref('')
const placeholder = ref(__('Type your message here...'))

function show() {
  nextTick(() => textareaRef.value?.el?.focus())
}

function sendTextMessage(event) {
  if (event?.shiftKey) return
  if (!props.conversationId || !content.value) return
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
      whatsapp.value?.reload?.()
    },
    onError: (error) => {
      content.value = messageContent
      toast.error(error.messages?.[0] || __('Failed to send message'))
    },
  })
}

defineExpose({ show })
</script>
