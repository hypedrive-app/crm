<!-- eslint-disable vue/no-v-html -->
<template>
  <div>
    <div v-if="messages.length" class="mb-3 flex items-center gap-2 px-3 sm:px-10">
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
      v-for="whatsapp in visibleMessages"
      :key="whatsapp.name"
      class="activity group flex gap-2"
      :class="[
        whatsapp.type == 'Outgoing' ? 'flex-row-reverse' : '',
        whatsapp.reaction ? 'mb-7' : 'mb-3',
        isGroupStart(whatsapp) ? 'mt-3 first:mt-0' : '',
      ]"
    >
      <div
        :id="whatsapp.name"
        class="group/message relative max-w-[90%] rounded-md bg-surface-gray-1 text-ink-gray-9 p-1.5 pl-2 text-base shadow-sm"
      >
        <Badge
          v-if="isFailed(whatsapp)"
          theme="red"
          :label="__('Failed')"
          class="absolute -top-2 right-0 z-10"
        />
        <div
          v-if="whatsapp.is_reply"
          class="mb-1 cursor-pointer rounded border-0 border-l-4 bg-surface-gray-3 p-2 text-ink-gray-5"
          :class="
            whatsapp.reply_to_type == 'Incoming'
              ? 'border-outline-green-3'
              : 'border-outline-blue-3'
          "
          @click="() => scrollToMessage(whatsapp.reply_to)"
        >
          <div
            class="mb-1 text-sm-bold"
            :class="
              whatsapp.reply_to_type == 'Incoming'
                ? 'text-ink-green-5'
                : 'text-ink-blue-link'
            "
          >
            {{ whatsapp.reply_to_from || __('You') }}
          </div>
          <div class="flex flex-col gap-2 max-h-12 overflow-hidden">
            <div v-if="whatsapp.header" class="text-base-semibold">
              {{ whatsapp.header }}
            </div>
            <div v-html="formatWhatsAppMarkup(whatsapp.reply_message)" />
            <div v-if="whatsapp.footer" class="text-xs text-ink-gray-5">
              {{ whatsapp.footer }}
            </div>
          </div>
        </div>
        <div class="flex gap-2 justify-between">
          <div
            v-if="whatsapp.reaction"
            class="absolute -bottom-5 flex gap-1 rounded-full border border-outline-gray-1 bg-surface-modal p-1 shadow-sm"
          >
            <div class="flex size-4 items-center justify-center">
              {{ whatsapp.reaction }}
            </div>
          </div>
          <div
            v-if="whatsapp.message_type == 'Template'"
            class="flex flex-col gap-2"
          >
            <div v-if="whatsapp.header" class="text-base-semibold">
              {{ whatsapp.header }}
            </div>
            <div v-html="formatWhatsAppMarkup(whatsapp.template)" />
            <div v-if="whatsapp.footer" class="text-xs text-ink-gray-5">
              {{ whatsapp.footer }}
            </div>
          </div>
          <div
            v-else-if="whatsapp.content_type == 'text'"
            v-html="formatWhatsAppMarkup(whatsapp.message)"
          />
          <div
            v-else-if="whatsapp.content_type == 'button'"
            class="flex items-center gap-1.5"
          >
            <span
              v-if="whatsapp.type == 'Incoming'"
              class="lucide-corner-up-left size-3.5 shrink-0 text-ink-gray-4"
              aria-hidden="true"
            />
            <span v-if="whatsapp.type == 'Incoming'" class="text-ink-gray-5">
              {{ __('Replied:') }}
            </span>
            <span
              class="text-sm-medium"
              v-html="formatWhatsAppMarkup(whatsapp.message)"
            />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'interactive'"
            class="flex flex-col gap-2"
          >
            <div v-html="formatWhatsAppMarkup(whatsapp.message)" />
            <div
              v-if="interactivePayload(whatsapp)?.type == 'button'"
              class="flex flex-wrap gap-1.5 border-t border-outline-gray-2 pt-2"
            >
              <div
                v-for="btn in interactivePayload(whatsapp).buttons"
                :key="btn.id"
                class="rounded-md border border-outline-gray-2 bg-surface-modal px-2.5 py-1 text-sm-medium text-ink-blue-link"
              >
                {{ btn.title }}
              </div>
            </div>
            <div
              v-else-if="interactivePayload(whatsapp)?.type == 'list'"
              class="flex flex-col gap-2 border-t border-outline-gray-2 pt-2"
            >
              <div
                v-for="(section, sIdx) in interactivePayload(whatsapp).sections"
                :key="sIdx"
                class="flex flex-col gap-1"
              >
                <div
                  v-if="section.title"
                  class="text-2xs font-medium uppercase text-ink-gray-4"
                >
                  {{ section.title }}
                </div>
                <div
                  v-for="row in section.rows"
                  :key="row.id"
                  class="rounded-md border border-outline-gray-2 bg-surface-modal px-2.5 py-1.5"
                >
                  <div class="text-sm-medium text-ink-blue-link">
                    {{ row.title }}
                  </div>
                  <div v-if="row.description" class="text-xs text-ink-gray-5">
                    {{ row.description }}
                  </div>
                </div>
              </div>
              <div
                class="mt-0.5 self-start rounded-md border border-outline-gray-2 px-2.5 py-1 text-sm-medium text-ink-blue-link"
              >
                {{ interactivePayload(whatsapp).listButtonLabel }}
              </div>
            </div>
          </div>
          <WhatsAppFlowMessage
            v-else-if="whatsapp.content_type == 'flow'"
            :whatsapp="whatsapp"
          />
          <div
            v-else-if="whatsapp.content_type == 'location' && locationPayload(whatsapp)"
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-modal p-2.5"
          >
            <div class="flex items-center gap-1.5 text-sm-medium text-ink-gray-8">
              <LocationIcon class="size-3.5 shrink-0 text-ink-gray-5" />
              <span class="truncate">
                {{ locationPayload(whatsapp).name || __('Shared Location') }}
              </span>
            </div>
            <div
              v-if="locationPayload(whatsapp).address"
              class="text-xs text-ink-gray-5"
            >
              {{ locationPayload(whatsapp).address }}
            </div>
            <div class="text-2xs text-ink-gray-4">
              {{ locationPayload(whatsapp).latitude }}, {{ locationPayload(whatsapp).longitude }}
            </div>
            <a
              :href="mapsUrl(locationPayload(whatsapp))"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-1 text-sm-medium text-ink-blue-link"
            >
              {{ __('View on Map') }}
            </a>
          </div>
          <div
            v-else-if="whatsapp.content_type == 'contact' && contactPayload(whatsapp)"
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-modal p-2.5"
          >
            <div class="flex items-center gap-1.5 text-sm-medium text-ink-gray-8">
              <ContactIcon class="size-3.5 shrink-0 text-ink-gray-5" />
              <span class="truncate">
                {{ contactPayload(whatsapp).formatted_name || __('Shared Contact') }}
              </span>
            </div>
            <div
              v-if="contactPayload(whatsapp).phone"
              class="text-xs text-ink-gray-5"
            >
              {{ contactPayload(whatsapp).phone }}
            </div>
          </div>
          <div v-else-if="whatsapp.content_type == 'image'">
            <img
              :src="whatsapp.attach"
              :alt="__('Image attachment')"
              class="max-h-40 w-auto max-w-full cursor-pointer rounded-md"
              @click="() => openFileInAnotherTab(whatsapp.attach)"
            />
            <div
              v-if="hasCaption(whatsapp)"
              class="mt-1.5"
              v-html="formatWhatsAppMarkup(whatsapp.message)"
            />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'document'"
            class="flex items-center gap-2"
          >
            <DocumentIcon
              class="size-10 shrink-0 cursor-pointer rounded-md text-ink-gray-4"
              @click="() => openFileInAnotherTab(whatsapp.attach)"
            />
            <a
              :href="whatsapp.attach"
              target="_blank"
              rel="noopener noreferrer"
              class="min-w-0 truncate text-ink-blue-link hover:underline"
            >
              {{ attachmentLabel(whatsapp) }}
            </a>
          </div>
          <div
            v-else-if="whatsapp.content_type == 'audio'"
            class="flex items-center gap-2"
          >
            <audio :src="whatsapp.attach" controls class="max-w-full" />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'video'"
            class="flex flex-col items-start gap-2"
          >
            <video
              :src="whatsapp.attach"
              controls
              class="max-h-40 w-auto max-w-full rounded-md"
            />
            <div
              v-if="hasCaption(whatsapp)"
              v-html="formatWhatsAppMarkup(whatsapp.message)"
            />
          </div>
          <div class="-mb-1 flex shrink-0 items-end gap-1 text-ink-gray-5">
            <Tooltip :text="formatDate(whatsapp.creation, 'ddd, MMM D, YYYY')">
              <div class="text-2xs">
                {{ formatDate(whatsapp.creation, 'hh:mm a') }}
              </div>
            </Tooltip>
            <DeliveryTick
              v-if="whatsapp.type == 'Outgoing'"
              :status="whatsapp.status"
            />
          </div>
        </div>
        <!-- Per-message actions. These act on THIS message (reply quotes it,
             a reaction attaches to it), so they belong with the bubble rather
             than in the thread header, which has no message to target. Kept in
             normal flow — the previous version floated them over the bubble's
             top-right corner on a hardcoded white radial gradient, which
             clipped the first line of text and broke in dark mode. Revealed on
             hover/focus on pointer devices; always visible on touch, where
             there is no hover to reveal them with. -->
        <div
          v-if="!isFailed(whatsapp)"
          class="mt-1 flex items-center gap-0.5 border-t border-outline-gray-1 pt-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover/message:opacity-100 sm:focus-within:opacity-100"
          :class="whatsapp.type == 'Outgoing' ? 'justify-end' : ''"
        >
          <Tooltip :text="__('Reply')">
            <Button
              variant="ghost"
              size="sm"
              :aria-label="__('Reply to this message')"
              @click="() => replyToMessage(whatsapp)"
            >
              <template #icon>
                <span
                  class="lucide-corner-up-left size-3.5 text-ink-gray-5"
                  aria-hidden="true"
                />
              </template>
            </Button>
          </Tooltip>
          <IconPicker
            v-slot="{ togglePopover }"
            v-model="emoji"
            v-model:reaction="reaction"
            @update:modelValue="() => reactOnMessage(whatsapp.name, emoji)"
          >
            <Tooltip :text="__('React')">
              <Button
                variant="ghost"
                size="sm"
                :aria-label="__('React to this message')"
                @click="() => (reaction = true) && togglePopover()"
              >
                <template #icon>
                  <ReactIcon class="size-3.5 text-ink-gray-5" />
                </template>
              </Button>
            </Tooltip>
          </IconPicker>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import IconPicker from '@/components/IconPicker.vue'
import DocumentIcon from '@/components/Icons/DocumentIcon.vue'
import ReactIcon from '@/components/Icons/ReactIcon.vue'
import WhatsAppFlowMessage from '@/components/Activities/WhatsAppFlowMessage.vue'
import LocationIcon from '@/components/Icons/LocationIcon.vue'
import ContactIcon from '@/components/Icons/ContactIcon.vue'
import ChatSearchBar from '@/components/Activities/ChatSearchBar.vue'
import DeliveryTick from '@/components/Activities/DeliveryTick.vue'
import {
  formatWhatsAppMarkup,
  useMessageGrouping,
  useMessageSearch,
} from '@/composables/useChatMessages'
import { formatDate } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import {
  Badge,
  Tooltip,
  Button,
  createResource,
  dayjs,
  toast,
} from 'frappe-ui'
import { computed, ref, toRef } from 'vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
})

const list = defineModel({ type: Object })

const { capture } = useTelemetry()

// Grouping and search come from the shared chat primitives, so this thread and
// the Chatwoot thread behave identically. The adapters below translate the
// WhatsApp Message doctype's own vocabulary into the neutral shape those
// primitives expect: `creation` is a SQL datetime string (not Chatwoot's epoch
// seconds), direction lives in `type` as 'Incoming'/'Outgoing', and there is no
// sender object at all — a thread is already one contact, so the phone number
// on the row is the only sender identity available.
const groupedMessages = useMessageGrouping(toRef(props, 'messages'), {
  direction: (m) => (m.type === 'Outgoing' ? 'outgoing' : 'incoming'),
  timestamp: (m) => (m.creation ? dayjs(m.creation).unix() : 0),
  senderId: (m) => (m.type === 'Outgoing' ? 'self' : m.from || m.profile_name || null),
  id: (m) => m.name,
  // A reaction pins a floating badge below its bubble and a reply renders a
  // quoted block above it; merging either into a tight run overlaps them with
  // the neighbouring bubble, so both always stand alone.
  standalone: (m) => Boolean(m.reaction || m.is_reply),
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
  // Search the rendered body, the template body and the caption — whichever
  // this row actually carries.
  text: (m) => `${m.message || ''} ${m.template || ''}`,
})

// The bubble template is per-message rather than per-group, so groups are
// flattened back to a flat list for rendering. Deliberately NOT spread into new
// objects: `interactivePayload` memoises parsed JSON in a WeakMap keyed on the
// message object itself, and a fresh copy per recompute would never hit that
// cache — re-parsing on every render, several times per bubble. The original
// row objects are passed through untouched and the run boundary is tracked in a
// parallel Set of message names instead.
const visibleMessages = computed(() =>
  visibleGroups.value.flatMap((group) => group.messages),
)

const groupStartNames = computed(
  () => new Set(visibleGroups.value.map((group) => group.messages[0]?.name)),
)

function isGroupStart(whatsapp) {
  return groupStartNames.value.has(whatsapp.name)
}

// Parses a WhatsApp Message's `buttons` JSON field (set by
// crm.api.whatsapp.send_whatsapp_interactive) into the shape the template
// above renders. Cached per-message so repeated renders in the same tick
// don't re-parse identical JSON.
const interactivePayloadCache = new WeakMap()

function interactivePayload(whatsapp) {
  if (!whatsapp?.buttons) return null
  if (interactivePayloadCache.has(whatsapp)) {
    return interactivePayloadCache.get(whatsapp)
  }
  let parsed = null
  try {
    const data =
      typeof whatsapp.buttons == 'string'
        ? JSON.parse(whatsapp.buttons)
        : whatsapp.buttons
    if (data?.type == 'button') {
      parsed = { type: 'button', buttons: data.buttons || [] }
    } else if (data?.type == 'list') {
      parsed = {
        type: 'list',
        listButtonLabel: data.list_button_label || __('Select Option'),
        sections: data.sections || [],
      }
    }
  } catch (e) {
    parsed = null
  }
  interactivePayloadCache.set(whatsapp, parsed)
  return parsed
}

// Parses a location WhatsApp Message's `product_catalog_json` field (already
// parsed to an object server-side by get_whatsapp_messages, but defensively
// handled here in case it arrives as a raw string) into the shape the
// map-pin card above renders.
function locationPayload(whatsapp) {
  const data = whatsapp?.product_catalog_json
  if (!data) return null
  try {
    const parsed = typeof data == 'string' ? JSON.parse(data) : data
    if (parsed?.latitude == null || parsed?.longitude == null) return null
    return parsed
  } catch (e) {
    return null
  }
}

function mapsUrl(location) {
  return `https://maps.google.com/?q=${location.latitude},${location.longitude}`
}

// Parses a contact WhatsApp Message's `product_catalog_json` field (a Meta
// `contacts` array — see send_whatsapp_contact / webhook.py's inbound
// "contacts" branch) into a flat {formatted_name, phone} for the contact card.
function contactPayload(whatsapp) {
  const data = whatsapp?.product_catalog_json
  if (!data) return null
  try {
    const parsed = typeof data == 'string' ? JSON.parse(data) : data
    const first = Array.isArray(parsed) ? parsed[0] : null
    if (!first) return null
    return {
      formatted_name: first.name?.formatted_name || '',
      phone: first.phones?.[0]?.phone || '',
    }
  } catch (e) {
    return null
  }
}

function openFileInAnotherTab(url) {
  window.open(url, '_blank')
}

// The WhatsApp Message doctype's `status` is a free-text Data field, not an
// enum: it carries app-level values ('Success', 'Failed') alongside Meta's own
// lowercase webhook strings ('sent', 'delivered', 'read'). A bare
// `status == 'failed'` therefore misses a row saved as 'Failed', which is what
// the app's own send path writes on error — so compare case-insensitively.
const FAILED_STATUSES = ['failed', 'failure', 'error']

function isFailed(whatsapp) {
  return FAILED_STATUSES.includes((whatsapp?.status || '').trim().toLowerCase())
}

// Inbound media arrives with the file path echoed into `message` when the
// sender attached no caption — rendering that path as the caption shows the
// user a raw '/files/...' string under their own image. Also guards the case
// where `message` is absent entirely, which crashed the previous
// `.startsWith()` check outright.
function hasCaption(whatsapp) {
  const message = whatsapp?.message
  if (typeof message !== 'string' || !message.trim()) return false
  return !message.startsWith('/files/') && !message.startsWith('/private/files/')
}

// Documents carry no filename field, so fall back to the basename of the
// stored file URL before a generic label.
function attachmentLabel(whatsapp) {
  const url = whatsapp?.attach || ''
  const basename = url.split('?')[0].split('/').pop()
  return basename ? decodeURIComponent(basename) : __('Document')
}

const emoji = ref('')
const reaction = ref(true)

function reactOnMessage(name, emoji) {
  createResource({
    url: 'crm.api.whatsapp.react_on_whatsapp_message',
    params: {
      emoji,
      reply_to_name: name,
    },
    auto: true,
    onSuccess() {
      capture('whatsapp_react_on_message')
      list.value.reload()
    },
    onError(error) {
      toast.error(
        error.messages?.[0] || __('Failed to add reaction to the message'),
      )
    },
  })
}

const reply = defineModel('reply', { type: Object, default: () => ({}) })

// Loads a message into the composer's quoted-reply slot. Previously reached
// through a single-item hover Dropdown; now a direct button, since a one-option
// menu was a click of pure overhead.
function replyToMessage(message) {
  reply.value = {
    ...message,
    message: formatWhatsAppMarkup(message.message),
  }
}

function scrollToMessage(name) {
  if (!name) return
  // The quoted message may not be in the DOM at all — replies commonly point
  // at messages older than the currently-loaded page, and the previous
  // implementation threw on the resulting null.
  const element = document.getElementById(name)
  if (!element) {
    toast.error(__('That message is not loaded in this conversation yet'))
    return
  }
  element.scrollIntoView({ behavior: 'smooth', block: 'center' })

  // Brief highlight so the eye lands on the right bubble. Uses the same
  // surface token as the rest of the thread so it reads correctly in dark mode
  // (the previous bg-yellow-100 was a hardcoded light-mode-only colour).
  element.classList.add('ring-2', 'ring-outline-amber-2')
  setTimeout(() => {
    element.classList.remove('ring-2', 'ring-outline-amber-2')
  }, 1200)
}
</script>
