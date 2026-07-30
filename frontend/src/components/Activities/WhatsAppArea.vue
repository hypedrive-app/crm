<!-- eslint-disable vue/no-v-html -->
<template>
  <div>
    <div
      v-for="whatsapp in messages"
      :key="whatsapp.name"
      class="activity group flex gap-2"
      :class="[
        whatsapp.type == 'Outgoing' ? 'flex-row-reverse' : '',
        whatsapp.reaction ? 'mb-7' : 'mb-3',
      ]"
    >
      <div
        :id="whatsapp.name"
        class="group/message relative max-w-[90%] rounded-md bg-surface-gray-1 text-ink-gray-9 p-1.5 pl-2 text-base shadow-sm"
      >
        <Badge
          v-if="whatsapp.status == 'failed'"
          theme="red"
          :label="whatsapp.status"
          class="absolute -top-2 right-0"
        />
        <div
          v-if="whatsapp.is_reply"
          class="mb-1 cursor-pointer rounded border-0 border-l-4 bg-surface-gray-3 p-2 text-ink-gray-5"
          :class="
            whatsapp.reply_to_type == 'Incoming'
              ? 'border-green-500'
              : 'border-blue-400'
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
            <div v-html="formatWhatsAppMessage(whatsapp.reply_message)" />
            <div v-if="whatsapp.footer" class="text-xs text-ink-gray-5">
              {{ whatsapp.footer }}
            </div>
          </div>
        </div>
        <div class="flex gap-2 justify-between">
          <div
            v-if="whatsapp.status != 'failed'"
            class="absolute -right-0.5 -top-0.5 flex cursor-pointer gap-1 rounded-full bg-surface-base pb-2 pl-2 pr-1.5 pt-1.5 opacity-0 group-hover/message:opacity-100"
            :style="{
              background:
                'radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 1) 35%, rgba(238, 130, 238, 0) 100%)',
            }"
          >
            <Dropdown :options="messageOptions(whatsapp)">
              <span
                class="lucide-chevron-down size-4 text-ink-gray-5"
                aria-hidden="true"
              />
            </Dropdown>
          </div>
          <div
            v-if="whatsapp.reaction"
            class="absolute -bottom-5 flex gap-1 rounded-full border bg-surface-base p-1 pb-[3px] shadow-sm"
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
            <div v-html="formatWhatsAppMessage(whatsapp.template)" />
            <div v-if="whatsapp.footer" class="text-xs text-ink-gray-5">
              {{ whatsapp.footer }}
            </div>
          </div>
          <div
            v-else-if="whatsapp.content_type == 'text'"
            v-html="formatWhatsAppMessage(whatsapp.message)"
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
              v-html="formatWhatsAppMessage(whatsapp.message)"
            />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'interactive'"
            class="flex flex-col gap-2"
          >
            <div v-html="formatWhatsAppMessage(whatsapp.message)" />
            <div
              v-if="interactivePayload(whatsapp)?.type == 'button'"
              class="flex flex-wrap gap-1.5 border-t border-outline-gray-2 pt-2"
            >
              <div
                v-for="btn in interactivePayload(whatsapp).buttons"
                :key="btn.id"
                class="rounded-md border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-sm-medium text-ink-blue-link"
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
                  class="rounded-md border border-outline-gray-2 bg-surface-white px-2.5 py-1.5"
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
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-white p-2.5"
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
            class="flex w-56 flex-col gap-1 rounded-md border border-outline-gray-2 bg-surface-white p-2.5"
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
              class="h-40 cursor-pointer rounded-md"
              @click="() => openFileInAnotherTab(whatsapp.attach)"
            />
            <div
              v-if="!whatsapp.message.startsWith('/files/')"
              class="mt-1.5"
              v-html="formatWhatsAppMessage(whatsapp.message)"
            />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'document'"
            class="flex items-center gap-2"
          >
            <DocumentIcon
              class="size-10 cursor-pointer rounded-md text-ink-gray-4"
              @click="() => openFileInAnotherTab(whatsapp.attach)"
            />
            <div class="text-ink-gray-5">Document</div>
          </div>
          <div
            v-else-if="whatsapp.content_type == 'audio'"
            class="flex items-center gap-2"
          >
            <audio :src="whatsapp.attach" controls class="cursor-pointer" />
          </div>
          <div
            v-else-if="whatsapp.content_type == 'video'"
            class="flex-col items-center gap-2"
          >
            <video
              :src="whatsapp.attach"
              controls
              class="h-40 cursor-pointer rounded-md"
            />
            <div
              v-if="!whatsapp.message.startsWith('/files/')"
              class="mt-1.5"
              v-html="formatWhatsAppMessage(whatsapp.message)"
            />
          </div>
          <div class="-mb-1 flex shrink-0 items-end gap-1 text-ink-gray-5">
            <Tooltip :text="formatDate(whatsapp.creation, 'ddd, MMM D, YYYY')">
              <div class="text-2xs">
                {{ formatDate(whatsapp.creation, 'hh:mm a') }}
              </div>
            </Tooltip>
            <div v-if="whatsapp.type == 'Outgoing'">
              <CheckIcon
                v-if="['sent', 'Success'].includes(whatsapp.status)"
                class="size-4"
              />
              <DoubleCheckIcon
                v-else-if="['read', 'delivered'].includes(whatsapp.status)"
                class="size-4"
                :class="{ 'text-ink-blue-5': whatsapp.status == 'read' }"
              />
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="whatsapp.status != 'failed'"
        class="flex items-center justify-center opacity-0 transition-all ease-in group-hover:opacity-100"
      >
        <IconPicker
          v-slot="{ togglePopover }"
          v-model="emoji"
          v-model:reaction="reaction"
          @update:modelValue="() => reactOnMessage(whatsapp.name, emoji)"
        >
          <Button
            class="rounded-full !size-6 mt-0.5"
            @click="() => (reaction = true) && togglePopover()"
          >
            <template #icon>
              <ReactIcon class="text-ink-gray-3" />
            </template>
          </Button>
        </IconPicker>
      </div>
    </div>
  </div>
</template>

<script setup>
import IconPicker from '@/components/IconPicker.vue'
import CheckIcon from '@/components/Icons/CheckIcon.vue'
import DoubleCheckIcon from '@/components/Icons/DoubleCheckIcon.vue'
import DocumentIcon from '@/components/Icons/DocumentIcon.vue'
import ReactIcon from '@/components/Icons/ReactIcon.vue'
import WhatsAppFlowMessage from '@/components/Activities/WhatsAppFlowMessage.vue'
import LocationIcon from '@/components/Icons/LocationIcon.vue'
import ContactIcon from '@/components/Icons/ContactIcon.vue'
import { formatDate, sanitizeHTML } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import { Tooltip, Dropdown, createResource, toast } from 'frappe-ui'
import { ref } from 'vue'

defineProps({
  messages: { type: Array, default: () => [] },
})

const list = defineModel({ type: Object })

const { capture } = useTelemetry()

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

function formatWhatsAppMessage(message) {
  // if message contains _text_, make it italic
  message = message.replace(/_(.*?)_/g, '<i>$1</i>')
  // if message contains *text*, make it bold
  message = message.replace(/\*(.*?)\*/g, '<b>$1</b>')
  // if message contains ~text~, make it strikethrough
  message = message.replace(/~(.*?)~/g, '<s>$1</s>')
  // if message contains ```text```, make it monospace
  message = message.replace(/```(.*?)```/g, '<code>$1</code>')
  // if message contains `text`, make it inline code
  message = message.replace(/`(.*?)`/g, '<code>$1</code>')
  // if message contains > text, make it a blockquote
  message = message.replace(/^> (.*)$/gm, '<blockquote>$1</blockquote>')
  // if contain /n, make it a new line
  message = message.replace(/\n/g, '<br>')
  // if contains *<space>text, make it a bullet point
  message = message.replace(/\* (.*?)(?=\s*\*|$)/g, '<li>$1</li>')
  message = message.replace(/- (.*?)(?=\s*-|$)/g, '<li>$1</li>')
  message = message.replace(/(\d+)\. (.*?)(?=\s*(\d+)\.|$)/g, '<li>$2</li>')

  return sanitizeHTML(message)
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
const replyMode = ref(false)

function messageOptions(message) {
  return [
    {
      label: 'Reply',
      onClick: () => {
        replyMode.value = true
        reply.value = {
          ...message,
          message: formatWhatsAppMessage(message.message),
        }
      },
    },
    // {
    //   label: 'Forward',
    //   onClick: () => console.log('Forward'),
    // },
    // {
    //   label: 'Delete',
    //   onClick: () => console.log('Delete'),
    // },
  ]
}

function scrollToMessage(name) {
  const element = document.getElementById(name)
  element.scrollIntoView({ behavior: 'smooth' })

  // Highlight the message
  element.classList.add('bg-yellow-100')
  setTimeout(() => {
    element.classList.remove('bg-yellow-100')
  }, 1000)
}
</script>
