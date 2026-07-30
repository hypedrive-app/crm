<!-- eslint-disable vue/no-v-html -->
<template>
  <div>
    <div
      v-if="activeConversationId"
      class="mb-3 flex flex-wrap items-center gap-2 px-3 sm:px-10"
    >
      <Tooltip :text="isResolved ? __('Reopen conversation') : __('Resolve conversation')">
        <Button
          size="sm"
          :loading="toggling"
          @click="$emit('toggleStatus', isResolved ? 'open' : 'resolved')"
        >
          <template #prefix>
            <span
              :class="isResolved ? 'lucide-rotate-ccw' : 'lucide-check-circle'"
              class="size-3.5"
              aria-hidden="true"
            />
          </template>
          {{ isResolved ? __('Reopen') : __('Resolve') }}
        </Button>
      </Tooltip>
      <Tooltip :text="__('Search in this conversation')">
        <Button
          size="sm"
          :variant="showSearch ? 'solid' : 'subtle'"
          @click="toggleSearch"
        >
          <template #prefix>
            <span class="lucide-search size-3.5" aria-hidden="true" />
          </template>
        </Button>
      </Tooltip>
      <div
        v-if="assignee?.name"
        class="flex items-center gap-1.5 rounded-md bg-surface-gray-1 py-1 pl-1 pr-2 text-p-sm text-ink-gray-7"
      >
        <Avatar :image="assignee.avatar" :label="assignee.name" size="sm" />
        <span>{{ __('Assigned to {0}', [assignee.name]) }}</span>
      </div>
      <a
        v-if="chatwootUrl"
        :href="chatwootUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="ml-auto flex shrink-0 items-center gap-1 text-p-sm text-ink-gray-5 hover:text-ink-gray-8"
      >
        {{ __('Open in Chatwoot') }}
        <span class="lucide-external-link size-3.5" aria-hidden="true" />
      </a>
    </div>
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
    <div v-if="showSearch" class="mb-3 px-3 sm:px-10">
      <TextInput
        ref="searchInputRef"
        v-model="searchQuery"
        :placeholder="__('Search in this chat')"
        class="w-full"
        @keydown.esc="onSearchEscape"
      >
        <template #prefix>
          <span class="lucide-search size-4 text-ink-gray-6" aria-hidden="true" />
        </template>
        <template v-if="searchQuery" #suffix>
          <span
            class="lucide-x size-4 cursor-pointer text-ink-gray-5 hover:text-ink-gray-7"
            aria-hidden="true"
            @click="clearSearch"
          />
        </template>
      </TextInput>
      <div
        v-if="searchQuery && !filteredGroupedMessages.length"
        class="mt-3 text-center text-p-sm text-ink-gray-5"
      >
        {{ __('No messages found for "{0}"', [searchQuery]) }}
      </div>
    </div>
    <div
      v-for="group in visibleGroupedMessages"
      :key="group.key"
      class="group flex gap-2 mb-3"
      :class="[group.direction == 'outgoing' ? 'justify-end' : '']"
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
          <div
            v-if="message.content"
            v-html="formatChatwootMessage(message.content)"
          />
          <div v-else class="italic text-ink-gray-5">
            {{ __('Template message') }}
          </div>
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
import { Tooltip, Button, TextInput, Avatar } from 'frappe-ui'
import { computed, h, nextTick, ref, watch } from 'vue'
import { formatDate, sanitizeHTML } from '@/utils'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  conversations: { type: Array, default: () => [] },
  activeConversationId: { type: [Number, String], default: null },
  status: { type: String, default: 'open' },
  toggling: { type: Boolean, default: false },
  assignee: { type: Object, default: null },
  chatwootUrl: { type: String, default: null },
})

defineEmits(['selectConversation', 'toggleStatus'])

const isResolved = computed(() => props.status === 'resolved')

// Pure client-side filter over the already-loaded thread — Chatwoot has no
// server-side conversation-scoped search endpoint, so there is nothing to
// call here; this only ever narrows `messages`, already fetched for display.
const showSearch = ref(false)
const searchQuery = ref('')
const searchInputRef = ref(null)

function toggleSearch() {
  showSearch.value = !showSearch.value
  if (showSearch.value) {
    nextTick(() => searchInputRef.value?.el?.focus())
  } else {
    searchQuery.value = ''
  }
}

function clearSearch() {
  searchQuery.value = ''
  nextTick(() => searchInputRef.value?.el?.focus())
}

// Escape clears first, closes the bar on a second press — same ladder as
// the reference implementation this mirrors.
function onSearchEscape() {
  if (searchQuery.value) {
    searchQuery.value = ''
  } else {
    showSearch.value = false
  }
}

// Switching conversations should never leave a stale query/open bar behind.
watch(
  () => props.activeConversationId,
  () => {
    showSearch.value = false
    searchQuery.value = ''
  },
)

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

// Filters ALREADY-GROUPED messages by text content — groups are filtered
// down to just the matching messages within them rather than dropping whole
// groups, so a single hit inside a multi-message run still renders with its
// group's sender/avatar context intact. Activity (system) groups have no
// searchable "content" worth matching against and are dropped entirely once
// a query is active, matching the reference implementation's intent (this is
// a message search, not a system-log search).
const filteredGroupedMessages = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return groupedMessages.value

  const result = []
  for (const group of groupedMessages.value) {
    if (group.direction === 'activity') continue
    const matches = group.messages.filter((m) =>
      (m.content || '').toLowerCase().includes(query),
    )
    if (matches.length) {
      result.push({ ...group, messages: matches })
    }
  }
  return result
})

const visibleGroupedMessages = computed(() =>
  searchQuery.value.trim() ? filteredGroupedMessages.value : groupedMessages.value,
)

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
