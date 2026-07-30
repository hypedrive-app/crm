<template>
  <div
    v-if="title !== 'Data'"
    class="flex items-center justify-between gap-2 text-lg-medium mx-3 mb-3 mt-4 sm:mx-10 sm:mb-4 sm:mt-8"
  >
    <div
      class="flex h-8 shrink-0 items-center text-2xl-semibold text-ink-gray-8"
    >
      {{ __(title) }}
    </div>
    <Button
      v-if="title == 'Emails'"
      variant="solid"
      :label="__('New Email')"
      iconLeft="plus"
      @click="emailBox.show = true"
    />
    <Button
      v-else-if="title == 'Comments'"
      variant="solid"
      :label="__('New Comment')"
      iconLeft="plus"
      @click="emailBox.showComment = true"
    />
    <MultiActionButton
      v-else-if="title == 'Calls'"
      variant="solid"
      :options="callActions"
    />
    <Button
      v-else-if="title == 'Events'"
      variant="solid"
      @click="modalRef.showEvent()"
    >
      <template #prefix>
        <EventIcon class="h-4 w-4" />
      </template>
      <span>{{ __('Schedule an Event') }}</span>
    </Button>
    <Button
      v-else-if="title == 'Notes'"
      variant="solid"
      :label="__('New Note')"
      iconLeft="plus"
      @click="modalRef.showNote()"
    />
    <Button
      v-else-if="title == 'Tasks'"
      variant="solid"
      :label="__('New Task')"
      iconLeft="plus"
      @click="modalRef.showTask()"
    />
    <Button
      v-else-if="title == 'Attachments'"
      variant="solid"
      :label="__('Upload Attachment')"
      iconLeft="plus"
      @click="showFilesUploader = true"
    />
    <div v-else-if="title == 'WhatsApp'" class="flex gap-2 shrink-0">
      <Button
        :label="__('Send Template')"
        @click="showWhatsappTemplates = true"
      />
      <Button
        :label="__('Send Flow')"
        @click="showWhatsappFlows = true"
      />
      <Button
        :label="__('Send Interactive')"
        @click="showWhatsappInteractive = true"
      />
      <Dropdown :options="whatsappMoreActions">
        <template #default="{ open }">
          <Button
            :label="__('More')"
            :iconRight="open ? 'chevron-up' : 'chevron-down'"
          />
        </template>
      </Dropdown>
      <Button
        variant="solid"
        :label="__('New Message')"
        iconLeft="plus"
        @click="whatsappBox.show()"
      />
    </div>
    <!-- Chatwoot has no create-new action of its own (no "start conversation"
    endpoint exists — conversations only originate from the customer's side or
    from Chatwoot itself), so instead of the generic New dropdown it gets the
    conversation switcher + Resolve/Search/Open-in-Chatwoot controls, living
    in the same header row as every other tab's actions rather than floating
    as a separate card inside the message body. -->
    <div
      v-else-if="title == 'Chatwoot' && chatwootActiveConversationId"
      class="flex flex-wrap items-center justify-end gap-1.5"
    >
      <div
        v-if="chatwootConversations.length > 1"
        class="flex flex-wrap gap-1 rounded-lg bg-surface-gray-2 p-1"
      >
        <button
          v-for="conv in chatwootConversations"
          :key="conv.id"
          type="button"
          class="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-p-sm transition-colors"
          :class="
            conv.id === chatwootActiveConversationId
              ? 'bg-surface-white text-ink-gray-9 text-sm-medium shadow-sm'
              : 'text-ink-gray-5 hover:text-ink-gray-7'
          "
          @click="$emit('selectChatwootConversation', conv.id)"
        >
          <span
            class="size-1.5 shrink-0 rounded-full"
            :class="conv.status === 'resolved' ? 'bg-ink-gray-4' : 'bg-ink-green-3'"
          />
          {{ chatwootConversationLabel(conv) }}
          <span
            v-if="conv.unread_count"
            class="rounded-full bg-surface-red-2 px-1.5 text-2xs text-ink-red-4"
          >
            {{ conv.unread_count }}
          </span>
        </button>
      </div>
      <Button
        size="sm"
        variant="subtle"
        :loading="chatwootToggling"
        @click="$emit('toggleChatwootStatus', chatwootStatus === 'resolved' ? 'open' : 'resolved')"
      >
        <template #prefix>
          <span
            :class="chatwootStatus === 'resolved' ? 'lucide-rotate-ccw' : 'lucide-check-circle'"
            class="size-3.5"
            aria-hidden="true"
          />
        </template>
        {{ chatwootStatus === 'resolved' ? __('Reopen') : __('Resolve') }}
      </Button>
      <Tooltip :text="__('Search in this conversation')">
        <Button
          size="sm"
          variant="subtle"
          @click="$emit('toggleChatwootSearch')"
        >
          <span class="lucide-search size-3.5" aria-hidden="true" />
        </Button>
      </Tooltip>
      <Tooltip v-if="chatwootUrl" :text="__('Open in Chatwoot')">
        <a
          :href="chatwootUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="flex size-7 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-1 hover:text-ink-gray-8"
        >
          <span class="lucide-external-link size-3.5" aria-hidden="true" />
        </a>
      </Tooltip>
    </div>
    <Dropdown v-else :options="defaultActions" @click.stop>
      <template #default="{ open }">
        <Button
          variant="solid"
          class="flex items-center gap-1"
          :label="__('New')"
          iconLeft="plus"
          :iconRight="open ? 'chevron-up' : 'chevron-down'"
        />
      </template>
    </Dropdown>
  </div>
</template>
<script setup>
import MultiActionButton from '@/components/MultiActionButton.vue'
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import EventIcon from '@/components/Icons/EventIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import LocationIcon from '@/components/Icons/LocationIcon.vue'
import ContactIcon from '@/components/Icons/ContactIcon.vue'
import { globalStore } from '@/stores/global'
import { whatsappEnabled } from '@/composables/whatsapp'
import { callEnabled } from '@/composables/telephony'
import { Dropdown, Button, Tooltip } from 'frappe-ui'
import { computed, h } from 'vue'
import { timeAgo } from '@/utils'

const props = defineProps({
  tabs: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  doc: { type: Object, default: () => ({}) },
  modalRef: { type: Object, default: () => ({}) },
  whatsappBox: { type: Object, default: () => ({}) },
  chatwootConversations: { type: Array, default: () => [] },
  chatwootActiveConversationId: { type: [Number, String], default: null },
  chatwootStatus: { type: String, default: 'open' },
  chatwootToggling: { type: Boolean, default: false },
  chatwootUrl: { type: String, default: null },
})

const { makeCall } = globalStore()

defineEmits(['selectChatwootConversation', 'toggleChatwootStatus', 'toggleChatwootSearch'])

const tabIndex = defineModel({ type: Number })
const showWhatsappTemplates = defineModel('showWhatsappTemplates', {
  type: Boolean,
})
const showWhatsappFlows = defineModel('showWhatsappFlows', {
  type: Boolean,
})
const showWhatsappInteractive = defineModel('showWhatsappInteractive', {
  type: Boolean,
})
const showWhatsappLocation = defineModel('showWhatsappLocation', {
  type: Boolean,
})
const showWhatsappContact = defineModel('showWhatsappContact', {
  type: Boolean,
})
const showFilesUploader = defineModel('showFilesUploader', { type: Boolean })
const emailBox = defineModel('emailBox', { type: Object, default: () => ({}) })

const defaultActions = computed(() => {
  let actions = [
    {
      icon: h(Email2Icon, { class: 'h-4 w-4' }),
      label: __('Email'),
      onClick: () => (emailBox.value.show = true),
    },
    {
      icon: h(CommentIcon, { class: 'h-4 w-4' }),
      label: __('Comment'),
      onClick: () => (emailBox.value.showComment = true),
    },
    {
      icon: h(EventIcon, { class: 'h-4 w-4' }),
      label: __('Schedule an Event'),
      onClick: () => props.modalRef.showEvent(),
    },
    {
      icon: h(PhoneIcon, { class: 'h-4 w-4' }),
      label: __('Log a Call'),
      onClick: () => props.modalRef.createCallLog(),
    },
    {
      icon: h(PhoneIcon, { class: 'h-4 w-4' }),
      label: __('Make a Call'),
      onClick: () => makeCall(props.doc.mobile_no),
      condition: () => callEnabled.value,
    },
    {
      icon: h(NoteIcon, { class: 'h-4 w-4' }),
      label: __('Note'),
      onClick: () => props.modalRef.showNote(),
    },
    {
      icon: h(TaskIcon, { class: 'h-4 w-4' }),
      label: __('Task'),
      onClick: () => props.modalRef.showTask(),
    },
    {
      icon: h(AttachmentIcon, { class: 'h-4 w-4' }),
      label: __('Upload Attachment'),
      onClick: () => (showFilesUploader.value = true),
    },
    {
      icon: h(WhatsAppIcon, { class: 'h-4 w-4' }),
      label: __('WhatsApp Message'),
      onClick: () => (tabIndex.value = getTabIndex('WhatsApp')),
      condition: () => whatsappEnabled.value,
    },
  ]
  return actions.filter((action) =>
    action.condition ? action.condition() : true,
  )
})

function getTabIndex(name) {
  return props.tabs.findIndex((tab) => tab.name === name)
}

// The switcher used to label every tab with the contact's name — useless
// once a contact has more than one conversation, since every tab reads
// identically. Status + recency is what actually distinguishes conversations
// in Chatwoot's own inbox UI, so mirror that instead.
function chatwootConversationLabel(conv) {
  const status = conv.status === 'resolved' ? __('Resolved') : __('Open')
  const last = conv.last_activity_at || conv.timestamp
  return last ? `${status} · ${timeAgo(last * 1000)}` : status
}

const whatsappMoreActions = computed(() => [
  {
    icon: h(LocationIcon, { class: 'h-4 w-4' }),
    label: __('Send Location'),
    onClick: () => (showWhatsappLocation.value = true),
  },
  {
    icon: h(ContactIcon, { class: 'h-4 w-4' }),
    label: __('Send Contact'),
    onClick: () => (showWhatsappContact.value = true),
  },
])

const callActions = computed(() => {
  let actions = [
    {
      label: __('Log a Call'),
      icon: 'plus',
      onClick: () => props.modalRef.createCallLog(),
    },
    {
      label: __('Make a Call'),
      icon: h(PhoneIcon, { class: 'h-4 w-4' }),
      onClick: () => makeCall(props.doc.mobile_no),
      condition: () => callEnabled.value,
    },
  ]

  return actions.filter((action) =>
    action.condition ? action.condition() : true,
  )
})
</script>
