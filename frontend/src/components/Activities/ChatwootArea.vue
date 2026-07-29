<!-- eslint-disable vue/no-v-html -->
<template>
  <div>
    <div
      v-if="conversations.length > 1"
      class="mb-3 flex flex-wrap gap-1.5 px-3 sm:px-10"
    >
      <Button
        v-for="conv in conversations"
        :key="conv.id"
        :variant="conv.id === activeConversationId ? 'solid' : 'subtle'"
        size="sm"
        @click="$emit('selectConversation', conv.id)"
      >
        {{ conv.meta?.sender?.name || conv.meta?.sender?.phone_number || `#${conv.id}` }}
      </Button>
    </div>
    <div
      v-for="message in messages"
      :key="message.id"
      class="activity group flex gap-2"
      :class="[message.direction == 'outgoing' ? 'flex-row-reverse' : '', 'mb-3']"
    >
      <div
        :id="`cw-msg-${message.id}`"
        class="group/message relative max-w-[90%] rounded-md bg-surface-gray-1 text-ink-gray-9 p-1.5 pl-2 text-base shadow-sm"
      >
        <div
          v-if="message.direction == 'activity'"
          class="text-center text-2xs text-ink-gray-4"
          v-html="formatChatwootMessage(message.content)"
        />
        <template v-else>
          <div
            v-if="message.sender?.name"
            class="mb-0.5 text-2xs text-ink-gray-5"
          >
            {{ message.sender.name }}
          </div>
          <div v-html="formatChatwootMessage(message.content || '')" />
          <div
            v-if="message.attachments?.length"
            class="mt-1.5 flex flex-col gap-1.5"
          >
            <div v-for="att in message.attachments" :key="att.id">
              <img
                v-if="att.file_type == 'image'"
                :src="att.data_url"
                class="h-40 cursor-pointer rounded-md"
                @click="() => openFileInAnotherTab(att.data_url)"
              />
              <a
                v-else
                :href="att.data_url"
                target="_blank"
                class="flex items-center gap-2 text-ink-blue-link underline"
              >
                {{ __('Attachment') }}
              </a>
            </div>
          </div>
          <div class="-mb-1 mt-1 flex shrink-0 items-end justify-end gap-1 text-ink-gray-5">
            <Tooltip :text="formatDate(message.created_at * 1000, 'ddd, MMM D, YYYY')">
              <div class="text-2xs">
                {{ formatDate(message.created_at * 1000, 'hh:mm a') }}
              </div>
            </Tooltip>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Tooltip, Button } from 'frappe-ui'
import { formatDate, sanitizeHTML } from '@/utils'

defineProps({
  messages: { type: Array, default: () => [] },
  conversations: { type: Array, default: () => [] },
  activeConversationId: { type: [Number, String], default: null },
})

defineEmits(['selectConversation'])

function openFileInAnotherTab(url) {
  window.open(url, '_blank')
}

function formatChatwootMessage(message) {
  if (!message) return ''
  message = message.replace(/\n/g, '<br>')
  return sanitizeHTML(message)
}
</script>
