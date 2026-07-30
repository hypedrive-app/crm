<!-- eslint-disable vue/no-v-html -->
<template>
  <div>
    <!-- No conversation resolved for this record. Chatwoot conversations are
         looked up live by the contact's phone/email, so a record whose contact
         has never messaged us simply has none — every control below keys off
         `activeConversationId`, so without this the tab rendered completely
         blank with no explanation of why. -->
    <div
      v-if="!hasThread"
      class="flex flex-col items-center gap-1 px-3 py-10 text-center sm:px-10"
    >
      <span
        class="lucide-message-square-dashed size-6 text-ink-gray-4"
        aria-hidden="true"
      />
      <div class="text-p-base text-ink-gray-7">
        {{ __('No Chatwoot conversation for this contact') }}
      </div>
      <div class="max-w-sm text-p-sm text-ink-gray-5">
        {{
          __(
            'Conversations are matched live by the phone number or email on this record. One will appear here as soon as this contact messages you.',
          )
        }}
      </div>
    </div>
    <div
      v-else-if="activeConversationId"
      class="mb-3 flex items-center gap-2 overflow-x-auto"
    >
      <template v-if="conversations.length > 1">
        <Button
          v-for="conv in conversations"
          :key="conv.id"
          size="sm"
          :variant="conv.id === activeConversationId ? 'solid' : 'subtle'"
          class="shrink-0"
          @click="$emit('selectConversation', conv.id)"
        >
          <template #prefix>
            <span
              class="size-1.5 shrink-0 rounded-full"
              :class="conv.status === 'resolved' ? 'bg-ink-gray-4' : 'bg-ink-green-3'"
            />
          </template>
          {{ conversationLabel(conv) }}
          <span
            v-if="conv.unread_count"
            class="ml-1 rounded-full bg-surface-red-2 px-1.5 text-2xs text-ink-red-4"
          >
            {{ conv.unread_count }}
          </span>
        </Button>
        <div class="h-5 w-px shrink-0 bg-outline-gray-2" />
      </template>
      <div class="flex shrink-0 items-center gap-2">
        <!-- Reopening changes Chatwoot's own status only. It does NOT restore
             the WhatsApp reply window — that 24h limit is enforced by Meta off
             the customer's last inbound message, so a reopened conversation can
             still be reply-locked (verified live: status 'open' with
             can_reply false). The tooltip says so, because the bare "Reopen"
             label otherwise implies you can now type a free-form reply. -->
        <Tooltip
          :text="
            isResolved
              ? __('Reopen in Chatwoot. If the 24h WhatsApp window has passed, you will still need a template to message first.')
              : __('Mark this conversation resolved in Chatwoot')
          "
        >
          <Button
            size="sm"
            variant="subtle"
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
            :aria-label="__('Search in this conversation')"
            @click="toggleSearch"
          >
            <span class="lucide-search size-3.5" aria-hidden="true" />
          </Button>
        </Tooltip>
        <!-- Deep-link out to the Chatwoot dashboard. Rendered as a real anchor
             (not an <a> nested inside a frappe-ui <Button>, which produced
             invalid <a>-in-<button> markup with a muddled hit area) styled to
             match the sibling subtle icon buttons. -->
        <Tooltip v-if="chatwootUrl" :text="__('Open in Chatwoot')">
          <a
            :href="chatwootUrl"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="__('Open in Chatwoot')"
            class="flex size-7 items-center justify-center rounded bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3 hover:text-ink-gray-8"
          >
            <span class="lucide-external-link size-3.5" aria-hidden="true" />
          </a>
        </Tooltip>
      </div>
    </div>
    <ChatSearchBar
      v-if="showSearch"
      ref="searchInputRef"
      v-model="searchQuery"
      :result-count="filteredGroups.length"
      @clear="clearSearch"
      @escape="onSearchEscape"
    />
    <div
      v-for="group in hasThread ? visibleGroups : []"
      :key="group.key"
      class="group flex gap-2 mb-3"
      :class="[group.direction == 'outgoing' ? 'justify-end' : '']"
    >
      <div
        v-if="group.direction == 'activity'"
        class="w-full text-center text-2xs text-ink-gray-4"
        v-html="formatPlainMessage(group.messages[0].content)"
      />
      <div v-else class="flex max-w-[90%] flex-col gap-0.5">
        <div
          v-for="(message, idx) in group.messages"
          :id="`cw-msg-${message.id}`"
          :key="message.id"
          class="group/message relative break-words p-1.5 pl-2 text-base text-ink-gray-9 shadow-sm"
          :class="
            group.direction == 'outgoing'
              ? 'rounded-lg rounded-tr-sm bg-surface-blue-2'
              : 'rounded-lg rounded-tl-sm bg-surface-gray-2'
          "
        >
          <div
            v-if="idx === 0 && message.sender?.name"
            class="mb-0.5 text-2xs text-ink-gray-5"
          >
            {{ message.sender.name }}
          </div>
          <!-- A shared location arriving through a Chatwoot-native WhatsApp
               inbox carries no `content` — its lat/long/name land on
               `content_attributes`. Without this branch it rendered as a blank
               "Template message" fallback (asymmetric with the native WhatsApp
               tab, which draws a proper map-pin card). -->
          <div
            v-if="locationPayload(message)"
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-modal p-2.5"
          >
            <div class="flex items-center gap-1.5 text-sm-medium text-ink-gray-8">
              <span
                class="lucide-map-pin size-3.5 shrink-0 text-ink-gray-5"
                aria-hidden="true"
              />
              <span class="truncate">
                {{ locationPayload(message).name || __('Shared Location') }}
              </span>
            </div>
            <div
              v-if="locationPayload(message).address"
              class="text-xs text-ink-gray-5"
            >
              {{ locationPayload(message).address }}
            </div>
            <a
              :href="mapsUrl(locationPayload(message))"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-1 text-sm-medium text-ink-blue-link"
            >
              {{ __('View on Map') }}
            </a>
          </div>
          <!-- A shared contact card: Chatwoot stores the vCard-shaped data on
               content_attributes.contacts (or .contact). Same asymmetry fix as
               location above. -->
          <div
            v-else-if="contactPayload(message)"
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-modal p-2.5"
          >
            <div class="flex items-center gap-1.5 text-sm-medium text-ink-gray-8">
              <span
                class="lucide-user size-3.5 shrink-0 text-ink-gray-5"
                aria-hidden="true"
              />
              <span class="truncate">
                {{ contactPayload(message).name || __('Shared Contact') }}
              </span>
            </div>
            <div
              v-if="contactPayload(message).phone"
              class="text-xs text-ink-gray-5"
            >
              {{ contactPayload(message).phone }}
            </div>
          </div>
          <div
            v-else-if="message.content"
            v-html="formatPlainMessage(message.content)"
          />
          <div v-else class="italic text-ink-gray-5">
            {{ templateFallbackLabel(message) }}
          </div>
          <div
            v-if="message.attachments?.length"
            class="mt-1.5 flex flex-col gap-1.5"
          >
            <div v-for="att in message.attachments" :key="att.id">
              <!-- Chatwoot attachment data_urls can be auth-gated/expired; on
                   load failure swap to a labeled fallback that still links out
                   rather than a broken glyph. -->
              <MediaUnavailable
                v-if="attFailed(att)"
                :label="attFallbackLabel(att)"
                :href="att.data_url"
              />
              <img
                v-else-if="att.file_type == 'image'"
                :src="att.data_url"
                :alt="__('Image attachment')"
                loading="lazy"
                class="max-h-40 w-auto max-w-full cursor-pointer rounded-md"
                @click="() => openFileInAnotherTab(att.data_url)"
                @error="() => markAttFailed(att)"
              />
              <video
                v-else-if="att.file_type == 'video'"
                :src="att.data_url"
                controls
                class="max-h-40 w-auto max-w-full rounded-md"
                @error="() => markAttFailed(att)"
              />
              <audio
                v-else-if="att.file_type == 'audio'"
                :src="att.data_url"
                controls
                class="w-56 max-w-full"
                @error="() => markAttFailed(att)"
              />
              <a
                v-else
                :href="att.data_url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex items-center gap-2 text-ink-blue-link hover:underline"
              >
                <DocumentIcon class="size-8 shrink-0 text-ink-gray-4" />
                <span class="truncate">
                  {{ attachmentLabel(att) }}
                </span>
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
import ChatSearchBar from '@/components/Activities/ChatSearchBar.vue'
import DeliveryTick from '@/components/Activities/DeliveryTick.vue'
import MediaUnavailable from '@/components/Activities/MediaUnavailable.vue'
import DocumentIcon from '@/components/Icons/DocumentIcon.vue'
import { Tooltip, Button } from 'frappe-ui'
import { computed, ref, toRef } from 'vue'
import {
  formatPlainMessage,
  useMessageGrouping,
  useMessageSearch,
} from '@/composables/useChatMessages'
import { formatDate, timeAgo } from '@/utils'

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

// A thread exists once there's an active conversation OR any messages have
// loaded. The empty-state and the thread key off this SAME flag so they are
// strictly mutually exclusive — previously the empty-state gated on
// `!activeConversationId` while the message list had no gate at all, so during
// the window where messages had loaded but the active id wasn't set yet, the
// "no conversation" placeholder rendered ON TOP of a populated thread.
const hasThread = computed(
  () => Boolean(props.activeConversationId) || props.messages.length > 0,
)

// Grouping and search both come from the shared chat primitives so this
// thread and the WhatsApp thread behave identically. Chatwoot's messages
// carry epoch-second `created_at` and a server-annotated `direction`.
const groupedMessages = useMessageGrouping(toRef(props, 'messages'), {
  direction: (m) => m.direction || 'unknown',
  timestamp: (m) => m.created_at || 0,
  senderId: (m) => m.sender?.id ?? m.sender?.name ?? null,
  id: (m) => m.id,
})

const {
  showSearch,
  searchQuery,
  searchInputRef,
  filteredGroups,
  visibleGroups,
  toggleSearch,
  clearSearch,
  onSearchEscape,
} = useMessageSearch(groupedMessages, {
  text: (m) => m.content || '',
  resetOn: toRef(props, 'activeConversationId'),
})

// Chatwoot's attachment objects carry no filename field of their own, so fall
// back to the basename of the storage URL before a generic label.
function attachmentLabel(attachment) {
  const url = attachment?.data_url || ''
  const basename = url.split('?')[0].split('/').pop()
  return basename ? decodeURIComponent(basename) : __('Attachment')
}

function openFileInAnotherTab(url) {
  // noopener/noreferrer: without it the opened tab gets a live window.opener
  // handle back to this app (reverse-tabnabbing).
  window.open(url, '_blank', 'noopener,noreferrer')
}

// Tracks attachments whose media failed to load (expired/auth-gated Chatwoot
// data_url) so the bubble can swap to a labeled fallback. Keyed on attachment
// id; the tick forces the getter to re-run when the Set mutates in place.
const failedAtt = new Set()
const failedAttTick = ref(0)

function markAttFailed(att) {
  if (att?.id == null || failedAtt.has(att.id)) return
  failedAtt.add(att.id)
  failedAttTick.value++
}

function attFailed(att) {
  return failedAttTick.value >= 0 && failedAtt.has(att?.id)
}

function attFallbackLabel(att) {
  const type = att?.file_type
  if (type === 'image') return __('Image unavailable')
  if (type === 'video') return __('Video unavailable')
  if (type === 'audio') return __('Audio unavailable')
  return __('Attachment unavailable')
}

// Chatwoot delivers a shared WhatsApp location as a message with no `content`,
// with the coordinates on `content_attributes`. Field naming varies across
// Chatwoot versions (a nested `location` object, or flat lat/long keys), so
// probe both shapes and return null unless real coordinates are present — a
// null result falls through to the normal text/template render, so this can
// never blank out an ordinary message.
function locationPayload(message) {
  const attrs = message?.content_attributes
  if (!attrs) return null
  const loc = attrs.location || attrs
  const lat = loc.latitude ?? loc.lat
  const long = loc.longitude ?? loc.lng ?? loc.long
  if (lat == null || long == null) return null
  return {
    latitude: lat,
    longitude: long,
    name: loc.name || loc.title || '',
    address: loc.address || '',
  }
}

function mapsUrl(location) {
  return `https://maps.google.com/?q=${location.latitude},${location.longitude}`
}

// Chatwoot stores a shared contact card on content_attributes (a `contacts`
// array or a single `contact`). Flatten to {name, phone} for the card; null
// falls through to the normal render, so ordinary messages are untouched.
function contactPayload(message) {
  const attrs = message?.content_attributes
  if (!attrs) return null
  const raw = Array.isArray(attrs.contacts)
    ? attrs.contacts[0]
    : attrs.contact || null
  if (!raw) return null
  const name =
    raw.name?.formatted_name || raw.formatted_name || raw.name || ''
  const phone =
    raw.phones?.[0]?.phone || raw.phone || raw.phone_number || ''
  if (!name && !phone) return null
  return { name: typeof name === 'string' ? name : '', phone }
}

// The switcher used to label every tab with the contact's name — useless
// once a contact has more than one conversation, since every tab reads
// identically (this is exactly why it shipped confusing: 2 conversations,
// both "Shivam Gupta", no way to tell them apart without clicking through).
// Status + recency is what actually distinguishes conversations in Chatwoot's
// own inbox UI, so mirror that instead.
function conversationLabel(conv) {
  const status = conv.status === 'resolved' ? __('Resolved') : __('Open')
  const last = conv.last_activity_at || conv.timestamp
  return last ? `${status} · ${timeAgo(last * 1000)}` : status
}

// Chatwoot's own /messages response never echoes the rendered template body
// back in `content` for a template send — only in `additional_attributes.
// template_params.name`, the Meta template's machine name. Surface that
// instead of a generic placeholder wherever it's available.
function templateFallbackLabel(message) {
  const name = message.additional_attributes?.template_params?.name
  return name ? __('Template: {0}', [name]) : __('Template message')
}
</script>
