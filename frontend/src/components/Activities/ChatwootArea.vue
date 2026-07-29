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
      v-for="group in groupedMessages"
      :key="group.key"
      class="group flex gap-2 mb-3"
      :class="[group.direction == 'outgoing' ? 'flex-row-reverse' : '']"
    >
      <div
        v-if="group.direction == 'activity'"
        class="w-full text-center text-2xs text-ink-gray-4"
        v-html="formatChatwootMessage(group.messages[0].content)"
      />
      <div v-else class="flex max-w-[90%] flex-col gap-0.5">
        <div
          v-for="(message, idx) in group.messages"
          :id="`cw-msg-${message.id}`"
          :key="message.id"
          class="group/message relative rounded-md bg-surface-gray-1 p-1.5 pl-2 text-base text-ink-gray-9 shadow-sm"
        >
          <div
            v-if="idx === 0 && message.sender?.name"
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
          <div
            class="-mb-1 mt-1 flex shrink-0 items-end justify-end gap-1 text-ink-gray-5"
          >
            <Tooltip
              :text="formatDate(message.created_at * 1000, 'ddd, MMM D, YYYY')"
            >
              <div class="text-2xs">
                {{ formatDate(message.created_at * 1000, 'hh:mm a') }}
              </div>
            </Tooltip>
            <DeliveryTick
              v-if="group.direction == 'outgoing'"
              :status="message.status"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Tooltip, Button } from 'frappe-ui'
import { computed, h } from 'vue'
import { formatDate, sanitizeHTML } from '@/utils'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  conversations: { type: Array, default: () => [] },
  activeConversationId: { type: [Number, String], default: null },
})

defineEmits(['selectConversation'])

// Consecutive messages from the same sender within a 60s window merge into
// one visual run (one avatar/name label, tight inner gap) — matching
// WhatsApp Web / Stream Chat's published default grouping window. Activity
// (system) messages and a message_type change (incoming <-> outgoing) always
// start a new group even if inside the window.
const GROUP_WINDOW_SECONDS = 60

const groupedMessages = computed(() => {
  const groups = []
  for (const message of props.messages) {
    const direction = message.direction || 'unknown'
    const last = groups[groups.length - 1]
    const sameBucket =
      last &&
      last.direction === direction &&
      direction !== 'activity' &&
      last.senderId === (message.sender?.id ?? message.sender?.name ?? null) &&
      message.created_at - last.lastCreatedAt <= GROUP_WINDOW_SECONDS

    if (sameBucket) {
      last.messages.push(message)
      last.lastCreatedAt = message.created_at
    } else {
      groups.push({
        key: `${direction}-${message.id}`,
        direction,
        senderId: message.sender?.id ?? message.sender?.name ?? null,
        lastCreatedAt: message.created_at,
        messages: [message],
      })
    }
  }
  return groups
})

function openFileInAnotherTab(url) {
  window.open(url, '_blank')
}

function formatChatwootMessage(message) {
  if (!message) return ''
  message = message.replace(/\n/g, '<br>')
  return sanitizeHTML(message)
}

// Delivery tick — visual state only (no text label), mirroring WhatsApp's own
// semantics: clock (sending/pending local echo) -> single check (sent) ->
// double check grey (delivered) -> double check blue (read) -> red ! (failed).
// Chatwoot's message object carries this natively as `status`.
const DeliveryTick = {
  props: { status: { type: String, default: '' } },
  render() {
    const status = this.status
    if (status === 'failed') {
      return h('span', {
        class: 'lucide-alert-circle size-3.5 text-ink-red-3',
        title: __('Failed to send'),
      })
    }
    if (status === 'read') {
      return h('span', {
        class: 'lucide-check-check size-3.5 text-ink-blue-4',
      })
    }
    if (status === 'delivered') {
      return h('span', {
        class: 'lucide-check-check size-3.5 text-ink-gray-5',
      })
    }
    if (status === 'sent') {
      return h('span', { class: 'lucide-check size-3.5 text-ink-gray-5' })
    }
    // sending / progress / no status yet -> local-echo "pending" clock
    return h('span', { class: 'lucide-clock size-3 text-ink-gray-4' })
  },
}
</script>
