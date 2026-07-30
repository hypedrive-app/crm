<template>
  <ActivityHeader
    v-model="tabIndex"
    v-model:showFilesUploader="showFilesUploader"
    v-model:emailBox="emailBox"
    :tabs="tabs"
    :title="title"
    :doc="doc"
    :whatsappBox="whatsappBox"
    :modalRef="modalRef"
  />
  <FadedScrollableDiv class="flex flex-col h-full overflow-y-auto">
    <div
      v-if="all_activities?.loading"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-2xl-medium text-ink-gray-4"
    >
      <LoadingIndicator class="h-6 w-6" />
      <span>{{ __('Loading...') }}</span>
    </div>
    <div v-else-if="title == 'Events'" class="h-full activity">
      <EventArea :doctype="doctype" :docname="docname" />
    </div>
    <div
      v-else-if="
        title == 'Chatwoot' &&
        (chatwootConversations.loading || chatwootMessages.loading) &&
        !chatwootConversations.data?.length
      "
      class="flex flex-1 flex-col items-center justify-center gap-3 text-2xl-medium text-ink-gray-4"
    >
      <LoadingIndicator class="h-6 w-6" />
      <span>{{ __('Loading...') }}</span>
    </div>
    <div
      v-else-if="
        activities?.length ||
        (whatsappMessages.data?.length && title == 'WhatsApp') ||
        (title == 'Chatwoot' && chatwootEnabled)
      "
      class="activities"
    >
      <div v-if="title == 'WhatsApp' && whatsappMessages.data?.length">
        <WhatsAppArea
          v-model="whatsappMessages"
          v-model:reply="replyMessage"
          class="px-3 sm:px-10"
          :messages="whatsappMessages.data"
        />
      </div>
      <div v-else-if="title == 'Chatwoot'">
        <ChatwootArea
          class="px-3 sm:px-10"
          :messages="chatwootMessages.data?.messages || []"
          :conversations="chatwootConversations.data || []"
          :active-conversation-id="activeChatwootConversationId"
          :status="activeChatwootStatus"
          :toggling="chatwootToggleResource.loading"
          :assignee="chatwootMessages.data?.assignee"
          :chatwoot-url="chatwootMessages.data?.chatwoot_url"
          @select-conversation="selectChatwootConversation"
          @toggle-status="toggleChatwootStatus"
        />
      </div>
      <div
        v-else-if="title == 'Notes'"
        class="grid grid-cols-1 gap-4 px-3 pb-3 sm:px-10 sm:pb-5 lg:grid-cols-2 xl:grid-cols-3"
      >
        <div
          v-for="note in activities"
          :key="note.name"
          @click="modalRef.showNote(note)"
        >
          <NoteArea v-model="all_activities" :note="note" />
        </div>
      </div>
      <div v-else-if="title == 'Comments'" class="pb-5">
        <div v-for="(comment, i) in activities" :key="comment.name">
          <div
            class="activity grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 px-3 sm:gap-4 sm:px-10"
          >
            <div
              class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-elevation-2"
              :class="
                i != activities.length - 1 ? 'before:h-full' : 'before:h-4'
              "
            >
              <div
                class="flex h-8 w-7 items-center justify-center bg-surface-base"
              >
                <CommentIcon class="text-ink-gray-8" />
              </div>
            </div>
            <CommentArea
              class="mb-4"
              :activity="comment"
              @reload="all_activities.reload()"
            />
          </div>
        </div>
      </div>
      <div v-else-if="title == 'Tasks'" class="px-3 pb-3 sm:px-10 sm:pb-5">
        <TaskArea :modalRef="modalRef" :tasks="activities" :doctype="doctype" />
      </div>
      <div v-else-if="title == 'Calls'" class="activity">
        <div v-for="(call, i) in activities" :key="call.name">
          <div
            class="activity grid grid-cols-[30px_minmax(auto,_1fr)] gap-4 px-3 sm:px-10"
          >
            <div
              class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-elevation-2"
              :class="
                i != activities.length - 1 ? 'before:h-full' : 'before:h-4'
              "
            >
              <div
                class="flex h-8 w-7 items-center justify-center bg-surface-base text-ink-gray-8"
              >
                <MissedCallIcon
                  v-if="call.status == 'No Answer'"
                  class="text-ink-red-8"
                />
                <DeclinedCallIcon v-else-if="call.status == 'Busy'" />
                <component
                  :is="
                    call.type == 'Incoming' ? InboundCallIcon : OutboundCallIcon
                  "
                  v-else
                />
              </div>
            </div>
            <CallArea class="mb-4" :activity="call" />
          </div>
        </div>
      </div>
      <div
        v-else-if="title == 'Attachments'"
        class="px-3 pb-3 sm:px-10 sm:pb-5"
      >
        <AttachmentArea
          :attachments="activities"
          @reload="all_activities.reload() && scroll()"
        />
      </div>
      <template v-else>
        <div
          v-for="(activity, i) in activities"
          :key="activity.name"
          class="activity px-3 sm:px-10"
          :class="
            ['Activity', 'Emails'].includes(title)
              ? 'grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4'
              : ''
          "
        >
          <div
            v-if="['Activity', 'Emails'].includes(title)"
            class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-elevation-2"
            :class="[
              i != activities.length - 1 ? 'before:h-full' : 'before:h-4',
            ]"
          >
            <div
              class="flex h-7 w-7 items-center justify-center bg-surface-base"
              :class="{
                'mt-2.5': ['communication'].includes(activity.activity_type),
                'bg-surface-base': ['added', 'removed', 'changed'].includes(
                  activity.activity_type,
                ),
                'h-8': [
                  'comment',
                  'communication',
                  'incoming_call',
                  'outgoing_call',
                ].includes(activity.activity_type),
              }"
            >
              <UserAvatar
                v-if="activity.activity_type == 'communication'"
                :user="activity.data.sender"
                size="md"
              />
              <MissedCallIcon
                v-else-if="
                  ['incoming_call', 'outgoing_call'].includes(
                    activity.activity_type,
                  ) && activity.status == 'No Answer'
                "
                class="text-ink-red-8"
              />
              <DeclinedCallIcon
                v-else-if="
                  ['incoming_call', 'outgoing_call'].includes(
                    activity.activity_type,
                  ) && activity.status == 'Busy'
                "
              />
              <component
                :is="activity.icon"
                v-else
                :class="
                  ['added', 'removed', 'changed'].includes(
                    activity.activity_type,
                  )
                    ? 'text-ink-gray-4'
                    : 'text-ink-gray-8'
                "
              />
            </div>
          </div>
          <div
            v-if="activity.activity_type == 'communication'"
            class="pb-5 mt-px"
          >
            <EmailArea :activity="activity" :emailBox="emailBox" />
          </div>
          <div
            v-else-if="activity.activity_type == 'comment'"
            :id="activity.name"
            class="mb-4"
          >
            <CommentArea
              :activity="activity"
              @reload="all_activities.reload()"
            />
          </div>
          <div
            v-else-if="activity.activity_type == 'attachment_log'"
            :id="activity.name"
            class="mb-4 flex flex-col gap-2 py-1.5"
          >
            <div class="flex items-center justify-stretch gap-2 text-base">
              <div
                class="inline-flex items-center flex-wrap gap-1.5 text-ink-gray-8 font-medium"
              >
                <span class="font-medium">{{ activity.owner_name }}</span>
                <span class="text-ink-gray-5">{{
                  __(activity.data.type)
                }}</span>
                <a
                  v-if="activity.data.file_url"
                  :href="activity.data.file_url"
                  target="_blank"
                >
                  <span>{{ activity.data.file_name }}</span>
                </a>
                <span v-else>{{ activity.data.file_name }}</span>
                <span
                  v-if="activity.data.is_private"
                  class="lucide-lock size-3"
                  aria-hidden="true"
                />
              </div>
              <div class="ml-auto whitespace-nowrap">
                <TimelineTimestamp :date="activity.creation" />
              </div>
            </div>
          </div>
          <div
            v-else-if="
              activity.activity_type == 'incoming_call' ||
              activity.activity_type == 'outgoing_call'
            "
            class="mb-4"
          >
            <CallArea :activity="activity" />
          </div>
          <div v-else class="mb-4 flex flex-col gap-2 py-1.5">
            <div class="flex items-center justify-stretch gap-2 text-base">
              <div
                v-if="activity.other_versions"
                class="inline-flex flex-wrap gap-1.5 text-ink-gray-8 font-medium"
              >
                <span>{{
                  activity.show_others ? __('Hide') : __('Show')
                }}</span>
                <span> +{{ activity.other_versions.length + 1 }} </span>
                <span>{{ __('changes from') }}</span>
                <span>{{ activity.owner_name }}</span>
                <Button
                  class="!size-4"
                  variant="ghost"
                  :icon="SelectIcon"
                  @click="activity.show_others = !activity.show_others"
                />
              </div>
              <div
                v-else
                class="inline-flex items-center flex-wrap gap-1 text-ink-gray-5"
              >
                <span class="font-medium text-ink-gray-8">
                  {{ activity.owner_name }}
                </span>
                <span v-if="activity.type">{{ __(activity.type) }}</span>
                <span
                  v-if="activity.data?.field_label"
                  class="max-w-xs truncate font-medium text-ink-gray-8"
                >
                  {{ __(activity.data.field_label) }}
                </span>
                <span v-if="activity.value">{{ __(activity.value) }}</span>
                <span
                  v-if="activity.data?.old_value"
                  class="max-w-xs font-medium text-ink-gray-8"
                >
                  <div
                    v-if="activity.options == 'User'"
                    class="flex items-center gap-1"
                  >
                    <UserAvatar :user="activity.data.old_value" size="xs" />
                    {{ getUser(activity.data.old_value).full_name }}
                  </div>
                  <div v-else class="truncate">
                    {{ activity.data.old_value }}
                  </div>
                </span>
                <span v-if="activity.to">{{ __('to') }}</span>
                <span
                  v-if="activity.data?.value"
                  class="max-w-xs font-medium text-ink-gray-8"
                >
                  <div
                    v-if="activity.options == 'User'"
                    class="flex items-center gap-1"
                  >
                    <UserAvatar :user="activity.data.value" size="xs" />
                    {{ getUser(activity.data.value).full_name }}
                  </div>
                  <div v-else class="truncate">
                    {{ activity.data.value }}
                  </div>
                </span>
              </div>

              <div class="ml-auto whitespace-nowrap">
                <TimelineTimestamp :date="activity.creation" />
              </div>
            </div>
            <div
              v-if="activity.other_versions && activity.show_others"
              class="flex flex-col gap-0.5"
            >
              <div
                v-for="a in sortByCreation([
                  activity,
                  ...activity.other_versions,
                ])"
                :key="a.creation"
                class="flex items-start justify-stretch gap-2 py-1.5 text-base"
              >
                <div class="inline-flex flex-wrap gap-1 text-ink-gray-5">
                  <span
                    v-if="a.data?.field_label"
                    class="max-w-xs truncate text-ink-gray-5"
                  >
                    {{ __(a.data.field_label) }}
                  </span>
                  <span
                    class="lucide-arrow-right mx-1 h-4 w-4 text-ink-gray-5"
                    aria-hidden="true"
                  />
                  <span v-if="a.type">
                    {{ startCase(__(a.type)) }}
                  </span>
                  <span
                    v-if="a.data?.old_value"
                    class="max-w-xs font-medium text-ink-gray-8"
                  >
                    <div
                      v-if="a.options == 'User'"
                      class="flex items-center gap-1"
                    >
                      <UserAvatar :user="a.data.old_value" size="xs" />
                      {{ getUser(a.data.old_value).full_name }}
                    </div>
                    <div v-else class="truncate">
                      {{ a.data.old_value }}
                    </div>
                  </span>
                  <span v-if="a.to">{{ __('to') }}</span>
                  <span
                    v-if="a.data?.value"
                    class="max-w-xs font-medium text-ink-gray-8"
                  >
                    <div
                      v-if="a.options == 'User'"
                      class="flex items-center gap-1"
                    >
                      <UserAvatar :user="a.data.value" size="xs" />
                      {{ getUser(a.data.value).full_name }}
                    </div>
                    <div v-else class="truncate">
                      {{ a.data.value }}
                    </div>
                  </span>
                </div>

                <div class="ml-auto whitespace-nowrap">
                  <TimelineTimestamp :date="a.creation" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
    <div v-else-if="title == 'Data'" class="h-full flex flex-col px-3 sm:px-10">
      <DataFields
        :doctype="doctype"
        :docname="docname"
        @beforeSave="(data) => emit('beforeSave', data)"
        @afterSave="(data) => emit('afterSave', data)"
      />
    </div>
    <EmptyState
      v-else
      :title="emptyText"
      :description="emptyTextDescription"
      :icon="emptyTextIcon"
      :top="top"
    />
  </FadedScrollableDiv>
  <div>
    <CommunicationArea
      v-if="['Emails', 'Comments', 'Activity'].includes(title)"
      ref="emailBox"
      v-model="doc"
      v-model:reload="reload_email"
      :doctype="doctype"
      @scroll="scroll"
    />
    <WhatsAppBox
      v-if="title == 'WhatsApp'"
      ref="whatsappBox"
      v-model="doc"
      v-model:reply="replyMessage"
      v-model:whatsapp="whatsappMessages"
      :doctype="doctype"
      :can-reply="whatsappCanReply"
      @send-template="showWhatsappTemplates = true"
      @send-flow="showWhatsappFlows = true"
      @send-interactive="showWhatsappInteractive = true"
      @send-location="showWhatsappLocation = true"
      @send-contact="showWhatsappContact = true"
      @scroll="scroll"
    />
    <ChatwootBox
      v-if="title == 'Chatwoot'"
      ref="chatwootBox"
      v-model:chatwoot="chatwootMessages"
      :doctype="doctype"
      :docname="docname"
      :conversation-id="activeChatwootConversationId"
      :can-reply="activeChatwootCanReply"
      @scroll="scroll"
    />
  </div>
  <WhatsappTemplateSelectorModal
    v-if="whatsappEnabled"
    v-model="showWhatsappTemplates"
    :doctype="doctype"
    @send="(t) => sendTemplate(t)"
  />
  <WhatsappFlowSelectorModal
    v-if="whatsappEnabled"
    v-model="showWhatsappFlows"
    :sending="sendFlowResource.loading"
    :sending-flow="sendingFlowName"
    :error-message="sendFlowError"
    @send-flow="(f) => sendFlow(f)"
  />
  <WhatsappInteractiveModal
    v-if="whatsappEnabled"
    v-model="showWhatsappInteractive"
    :sending="sendInteractiveResource.loading"
    @send="(i) => sendInteractive(i)"
  />
  <WhatsappLocationModal
    v-if="whatsappEnabled"
    v-model="showWhatsappLocation"
    :sending="sendLocationResource.loading"
    @send="(l) => sendLocation(l)"
  />
  <WhatsappContactModal
    v-if="whatsappEnabled"
    v-model="showWhatsappContact"
    :sending="sendContactResource.loading"
    @send="(c) => sendContact(c)"
  />
  <AllModals
    ref="modalRef"
    v-model="all_activities"
    :doctype="doctype"
    :doc="doc"
  />
  <FilesUploader
    v-model="showFilesUploader"
    :doctype="doctype"
    :docname="docname"
    @after="
      () => {
        all_activities.reload()
        changeTabTo('attachments')
      }
    "
  />
</template>
<script setup>
import ActivityHeader from '@/components/Activities/ActivityHeader.vue'
import EmailArea from '@/components/Activities/EmailArea.vue'
import CommentArea from '@/components/Activities/CommentArea.vue'
import CallArea from '@/components/Activities/CallArea.vue'
import NoteArea from '@/components/Activities/NoteArea.vue'
import TaskArea from '@/components/Activities/TaskArea.vue'
import AttachmentArea from '@/components/Activities/AttachmentArea.vue'
import DataFields from '@/components/Activities/DataFields.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ActivityIcon from '@/components/Icons/ActivityIcon.vue'
import EmailIcon from '@/components/Icons/EmailIcon.vue'
import DetailsIcon from '@/components/Icons/DetailsIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import ChatwootIcon from '@/components/Icons/ChatwootIcon.vue'
import EventArea from '@/components/Activities/EventArea.vue'
import WhatsAppArea from '@/components/Activities/WhatsAppArea.vue'
import WhatsAppBox from '@/components/Activities/WhatsAppBox.vue'
import ChatwootArea from '@/components/Activities/ChatwootArea.vue'
import ChatwootBox from '@/components/Activities/ChatwootBox.vue'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import DealsIcon from '@/components/Icons/DealsIcon.vue'
import DotIcon from '@/components/Icons/DotIcon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import SelectIcon from '@/components/Icons/SelectIcon.vue'
import MissedCallIcon from '@/components/Icons/MissedCallIcon.vue'
import DeclinedCallIcon from '@/components/Icons/DeclinedCallIcon.vue'
import InboundCallIcon from '@/components/Icons/InboundCallIcon.vue'
import OutboundCallIcon from '@/components/Icons/OutboundCallIcon.vue'
import FadedScrollableDiv from '@/components/FadedScrollableDiv.vue'
import CommunicationArea from '@/components/CommunicationArea.vue'
import WhatsappTemplateSelectorModal from '@/components/Modals/WhatsappTemplateSelectorModal.vue'
import WhatsappFlowSelectorModal from '@/components/Modals/WhatsappFlowSelectorModal.vue'
import WhatsappInteractiveModal from '@/components/Modals/WhatsappInteractiveModal.vue'
import WhatsappLocationModal from '@/components/Modals/WhatsappLocationModal.vue'
import WhatsappContactModal from '@/components/Modals/WhatsappContactModal.vue'
import AllModals from '@/components/Activities/AllModals.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import TimelineTimestamp from '@/components/Activities/TimelineTimestamp.vue'
import { startCase } from '@/utils'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { useTimelinePreferences } from '@/composables/useTimelinePreferences'
import { whatsappEnabled } from '@/composables/whatsapp'
import { chatwootEnabled } from '@/composables/chatwoot'
import { useDocument } from '@/data/document'
import { useTelemetry } from 'frappe-ui/frappe'
import { Button, createResource, toast } from 'frappe-ui'
import { useElementVisibility } from '@vueuse/core'
import {
  ref,
  computed,
  h,
  markRaw,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount,
} from 'vue'
import { useRoute } from 'vue-router'

const { $socket } = globalStore()
const { getUser } = usersStore()
const { capture } = useTelemetry()
const { isNewestFirst } = useTimelinePreferences()

const props = defineProps({
  doctype: { type: String, default: 'CRM Lead' },
  docname: { type: String, default: '' },
  tabs: { type: Array, default: () => [] },
})

const emit = defineEmits(['beforeSave', 'afterSave'])

const route = useRoute()

const reload = defineModel('reload', { type: Boolean, default: false })
const tabIndex = defineModel('tabIndex', { type: Number, default: 0 })

const { document: _document } = useDocument(props.doctype, props.docname)

const doc = computed(() => _document.doc || {})

const reload_email = ref(false)
const modalRef = ref(null)
const showFilesUploader = ref(false)

const title = computed(() => props.tabs?.[tabIndex.value]?.name || 'Activity')

const changeTabTo = (tabName) => {
  const tabNames = props.tabs?.map((tab) => tab.name?.toLowerCase())
  const index = tabNames?.indexOf(tabName)
  if (index == -1) return
  tabIndex.value = index
}

const all_activities = createResource({
  url: 'crm.api.activities.get_activities',
  params: { name: props.docname },
  cache: ['activity', props.docname],
  auto: true,
  transform: ([versions, calls, notes, tasks, attachments]) => {
    return { versions, calls, notes, tasks, attachments }
  },
  onSuccess: () => nextTick(() => scroll()),
})

const showWhatsappTemplates = ref(false)
const showWhatsappFlows = ref(false)
const sendingFlowName = ref('')
const sendFlowError = ref('')
const showWhatsappInteractive = ref(false)
const showWhatsappLocation = ref(false)
const showWhatsappContact = ref(false)

const whatsappMessages = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_messages',
  cache: ['whatsapp_messages', props.docname],
  params: {
    reference_doctype: props.doctype,
    reference_name: props.docname,
  },
  auto: false,
  transform: (data) => sortByCreation(data),
  onSuccess: () => nextTick(() => scroll()),
})

// Meta's 24-hour customer-service window for the NATIVE WhatsApp tab — the
// same constraint Chatwoot exposes as `can_reply`, but the native
// frappe_whatsapp path has no equivalent, so an agent could type free text into
// an expired thread and only learn it failed after Meta's round-trip. This
// resource mirrors the Chatwoot behaviour: it reports whether a free-form
// (non-template) reply will be accepted, so WhatsAppBox can lock the composer
// and steer to a template instead.
const whatsappReplyWindow = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_reply_window',
  params: {
    reference_doctype: props.doctype,
    reference_name: props.docname,
  },
  auto: false,
})

// Default to repliable while unknown (null/loading) so the composer is never
// gratuitously locked on a slow fetch — a free-form send during that window
// still fails safe (the send path surfaces Meta's rejection), whereas a
// wrongly-locked composer blocks a legitimate reply with no recourse.
const whatsappCanReply = computed(
  () => whatsappReplyWindow.data?.can_reply !== false,
)

watch(
  whatsappEnabled,
  (enabled) => {
    if (enabled) {
      whatsappMessages.fetch()
      whatsappReplyWindow.fetch()
    }
  },
  { immediate: true },
)

// The window is anchored on the customer's LAST inbound message, so it moves
// every time they reply — refetch whenever the thread changes or the tab is
// opened, keeping the lock state honest without a dedicated realtime channel.
watch(
  [title, () => whatsappMessages.data],
  () => {
    if (title.value === 'WhatsApp' && whatsappEnabled.value) {
      whatsappReplyWindow.fetch()
    }
  },
)

// Mark unread inbound WhatsApp messages as read once the tab is actually
// being viewed — matching how WhatsApp/Telegram themselves mark read on
// open rather than requiring an explicit action. Guarded by a name set so
// re-renders/polling ticks for messages we've already sent a receipt for
// don't re-fire the API; new inbound messages arriving while the tab stays
// open (realtime reload above) still get picked up since they add new
// names to the unread list.
const markedWhatsappReadNames = new Set()

function markWhatsappMessagesReadIfNeeded() {
  if (title.value !== 'WhatsApp') return
  const unread = (whatsappMessages.data || []).filter(
    (message) =>
      message.type == 'Incoming' &&
      message.status != 'marked as read' &&
      !markedWhatsappReadNames.has(message.name),
  )
  if (!unread.length) return
  unread.forEach((message) => markedWhatsappReadNames.add(message.name))
  createResource({
    url: 'crm.api.whatsapp.mark_whatsapp_messages_read',
    params: {
      reference_doctype: props.doctype,
      reference_name: props.docname,
    },
    auto: true,
  })
}

watch(
  [title, () => whatsappMessages.data],
  () => nextTick(markWhatsappMessagesReadIfNeeded),
  { immediate: true },
)

const activeChatwootConversationId = ref(null)

// Chatwoot itself reports whether a conversation currently accepts new agent
// replies (e.g. false once a WhatsApp conversation has been outside Meta's
// 24-hour customer-service window for a while — a real, common WhatsApp
// Business API constraint, not a bug in our integration). We weren't reading
// this field at all, so a legitimately un-repliable conversation looked
// identical to a broken/loading reply box with zero explanation.
const activeChatwootCanReply = computed(() => {
  const conversation = chatwootConversations.data?.find(
    (c) => c.id === activeChatwootConversationId.value,
  )
  return conversation ? conversation.can_reply !== false : true
})

// Conversation status (open/resolved/pending/snoozed) for the header
// resolve/reopen toggle. Sourced from the conversation list (same place
// can_reply comes from) rather than the messages resource, so it reflects
// the latest known state immediately after a toggle without waiting on a
// full message reload.
const activeChatwootStatus = computed(() => {
  const conversation = chatwootConversations.data?.find(
    (c) => c.id === activeChatwootConversationId.value,
  )
  return conversation?.status || 'open'
})

const chatwootToggleResource = createResource({
  url: 'crm.api.chatwoot.toggle_chatwoot_status',
  auto: false,
  onSuccess: (result) => {
    const conversation = chatwootConversations.data?.find(
      (c) => c.id === activeChatwootConversationId.value,
    )
    const newStatus = result?.status || conversation?.status
    if (conversation) {
      conversation.status = newStatus
    }
    toast.success(
      newStatus === 'resolved' ? __('Conversation resolved') : __('Conversation reopened'),
    )
  },
  onError: (error) => {
    toast.error(error.messages?.[0] || __('Failed to update conversation status'))
  },
})

function toggleChatwootStatus(nextStatus) {
  if (!activeChatwootConversationId.value || chatwootToggleResource.loading) return
  chatwootToggleResource.submit({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    conversation_id: activeChatwootConversationId.value,
    status: nextStatus,
  })
}

const chatwootConversations = createResource({
  url: 'crm.api.chatwoot.get_chatwoot_conversations',
  cache: ['chatwoot_conversations', props.docname],
  params: {
    reference_doctype: props.doctype,
    reference_name: props.docname,
  },
  auto: false,
  onSuccess: (data) => {
    if (data?.length && !activeChatwootConversationId.value) {
      activeChatwootConversationId.value = data[0].id
      chatwootMessages.fetch()
    }
  },
})

const chatwootMessages = createResource({
  url: 'crm.api.chatwoot.get_chatwoot_messages',
  // Must include conversation_id: a lead/deal can have multiple Chatwoot
  // conversations, and this resource is refetched in place (fetch()) when
  // the active conversation changes. Without conversation_id in the cache
  // key, switching conversations (or the auto-select-first-conversation on
  // reload) can serve/overwrite the cache with another conversation's
  // messages under the same slot — messages sent to a since-deselected
  // conversation then silently vanish from view even though the send
  // succeeded and the backend has them.
  cache: ['chatwoot_messages', props.docname, activeChatwootConversationId],
  makeParams: () => ({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    conversation_id: activeChatwootConversationId.value,
  }),
  auto: false,
  onSuccess: (data) => {
    chatwootSinceId.value = maxMessageId(data?.messages)
    nextTick(() => scroll())
  },
})

// Cursor for incremental polling (see get_new_chatwoot_messages /
// frappe_chatwoot's bounded after=-drain). Seeded from the max message id of
// the last full load; advanced on every incremental merge so a realtime tick
// only ever pulls what's new instead of refetching full history each time.
const chatwootSinceId = ref(null)

function maxMessageId(messages) {
  if (!messages?.length) return null
  return messages.reduce((max, m) => (m.id > max ? m.id : max), messages[0].id)
}

function selectChatwootConversation(conversationId) {
  activeChatwootConversationId.value = conversationId
  chatwootSinceId.value = null
  chatwootMessages.fetch()
}

function fetchNewChatwootMessages() {
  if (!activeChatwootConversationId.value) return
  if (!chatwootSinceId.value) {
    // No cursor yet (tab never fully loaded) — fall back to a normal load.
    chatwootMessages.fetch()
    return
  }
  createResource({
    url: 'crm.api.chatwoot.get_new_chatwoot_messages',
    params: {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      conversation_id: activeChatwootConversationId.value,
      since_id: chatwootSinceId.value,
    },
    auto: true,
    onSuccess: (result) => {
      const incoming = result?.messages || []
      if (incoming.length && chatwootMessages.data) {
        const existingIds = new Set(
          chatwootMessages.data.messages.map((m) => m.id),
        )
        const merged = [
          ...chatwootMessages.data.messages,
          ...incoming.filter((m) => !existingIds.has(m.id)),
        ]
        chatwootMessages.data.messages = merged
        nextTick(() => scroll())
      }
      if (result?.max_id_seen) {
        chatwootSinceId.value = result.max_id_seen
      }
      // Drain wasn't finished (>100 backlog) — immediately continue rather
      // than waiting for the next realtime tick, per get_new_messages'
      // documented truncated=True contract.
      if (result?.truncated) {
        fetchNewChatwootMessages()
      }
    },
  })
}

watch(
  chatwootEnabled,
  (enabled) => {
    if (enabled) chatwootConversations.fetch()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  $socket.off('whatsapp_message')
  $socket.off('chatwoot_message')
  $socket.off('docinfo_update', handleDocinfoUpdate)
  $socket.emit('doc_unsubscribe', props.doctype, props.docname)
})

onMounted(() => {
  $socket.emit('doc_subscribe', props.doctype, props.docname)
  $socket.on('docinfo_update', handleDocinfoUpdate)
  $socket.on('whatsapp_message', (data) => {
    if (
      data.reference_doctype === props.doctype &&
      data.reference_name === props.docname
    ) {
      whatsappMessages.reload()
    }
  })
  $socket.on('chatwoot_message', (data) => {
    // Minimal signal payload (conversation_id/inbox_id/updated_at only, no
    // message body — see frappe_chatwoot's realtime_bridge.py docstring).
    // We don't know which conversation belongs to THIS record client-side
    // without re-querying, so refetch the conversation list; if the active
    // conversation matches, pull only what's new via the incremental
    // since_id cursor rather than reloading the full thread on every tick.
    chatwootConversations.reload()
    if (data.conversation_id === activeChatwootConversationId.value) {
      fetchNewChatwootMessages()
    }
  })

  nextTick(() => {
    const hash = route.hash.slice(1) || null
    let tabNames = props.tabs?.map((tab) => tab.name)
    if (!tabNames?.includes(hash)) {
      scroll(hash)
    }
  })
})

function handleDocinfoUpdate({ doc, key }) {
  if (key !== 'comments') return
  if (doc.reference_doctype !== props.doctype) return
  if (doc.reference_name !== props.docname) return

  all_activities.reload()
  _document.reload()
}

function sendTemplate({ template, bodyParameters, headerParameters }) {
  capture('send_whatsapp_template', { doctype: props.doctype })
  createResource({
    url: 'crm.api.whatsapp.send_whatsapp_template',
    params: {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      to: doc.value.mobile_no,
      template,
      body_parameters: bodyParameters,
      header_parameters: headerParameters,
    },
    auto: true,
    onError: (error) => {
      toast.error(error.messages?.[0] || __('Failed to send WhatsApp template'))
    },
    // Only dismiss the dialog once the send is confirmed to have gone
    // through — closing unconditionally (as before) hid genuine failures
    // (e.g. Meta rejecting an AUTHENTICATION-category template) behind a
    // dialog that appeared to close as if the send had succeeded.
    onSuccess: () => {
      showWhatsappTemplates.value = false
      whatsappMessages.reload()
    },
  })
}

const sendFlowResource = createResource({
  url: 'crm.api.whatsapp.send_whatsapp_flow',
  onError: (error) => {
    sendFlowError.value = error.messages?.[0] || __('Failed to send WhatsApp Flow')
  },
  // Only dismiss the dialog once the send is confirmed to have gone
  // through, mirroring sendTemplate above.
  onSuccess: () => {
    sendingFlowName.value = ''
    showWhatsappFlows.value = false
    whatsappMessages.reload()
  },
})

function sendFlow(flow) {
  capture('send_whatsapp_flow', { doctype: props.doctype })
  sendFlowError.value = ''
  sendingFlowName.value = flow.name
  sendFlowResource.submit({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    to: doc.value.mobile_no,
    flow: flow.name,
  })
}

const sendInteractiveResource = createResource({
  url: 'crm.api.whatsapp.send_whatsapp_interactive',
  onError: (error) => {
    toast.error(
      error.messages?.[0] || __('Failed to send WhatsApp interactive message'),
    )
  },
  // Only dismiss the dialog once the send is confirmed to have gone
  // through, mirroring sendTemplate/sendFlow above.
  onSuccess: () => {
    showWhatsappInteractive.value = false
    whatsappMessages.reload()
  },
})

function sendInteractive({ interactiveType, message, buttons, listButtonLabel, sections }) {
  capture('send_whatsapp_interactive', { doctype: props.doctype })
  sendInteractiveResource.submit({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    to: doc.value.mobile_no,
    message,
    interactive_type: interactiveType,
    buttons: buttons || [],
    list_button_label: listButtonLabel || '',
    sections: sections || [],
    reply_to: replyMessage.value?.name || '',
  })
}

const sendLocationResource = createResource({
  url: 'crm.api.whatsapp.send_whatsapp_location',
  onError: (error) => {
    toast.error(error.messages?.[0] || __('Failed to send WhatsApp location'))
  },
  // Only dismiss the dialog once the send is confirmed to have gone
  // through, mirroring sendTemplate/sendFlow/sendInteractive above.
  onSuccess: () => {
    showWhatsappLocation.value = false
    whatsappMessages.reload()
  },
})

function sendLocation({ latitude, longitude, name, address }) {
  capture('send_whatsapp_location', { doctype: props.doctype })
  sendLocationResource.submit({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    to: doc.value.mobile_no,
    latitude,
    longitude,
    name: name || '',
    address: address || '',
    reply_to: replyMessage.value?.name || '',
  })
}

const sendContactResource = createResource({
  url: 'crm.api.whatsapp.send_whatsapp_contact',
  onError: (error) => {
    toast.error(error.messages?.[0] || __('Failed to send WhatsApp contact'))
  },
  onSuccess: () => {
    showWhatsappContact.value = false
    whatsappMessages.reload()
  },
})

function sendContact({ contactName, phone }) {
  capture('send_whatsapp_contact', { doctype: props.doctype })
  sendContactResource.submit({
    reference_doctype: props.doctype,
    reference_name: props.docname,
    to: doc.value.mobile_no,
    contact_name: contactName,
    phone,
    reply_to: replyMessage.value?.name || '',
  })
}

const replyMessage = ref({})

function get_activities() {
  if (!all_activities.data?.versions) return []
  if (!all_activities.data?.calls.length)
    return all_activities.data.versions || []
  return [...all_activities.data.versions, ...all_activities.data.calls]
}

const activities = computed(() => {
  let _activities = []
  if (title.value == 'Activity') {
    _activities = get_activities()
  } else if (title.value == 'Emails') {
    if (!all_activities.data?.versions) return []
    _activities = all_activities.data.versions.filter(
      (activity) => activity.activity_type === 'communication',
    )
  } else if (title.value == 'Comments') {
    if (!all_activities.data?.versions) return []
    _activities = all_activities.data.versions.filter(
      (activity) => activity.activity_type === 'comment',
    )
  } else if (title.value == 'Calls') {
    if (!all_activities.data?.calls) return []
    return sortByCreation(all_activities.data.calls, isNewestFirst.value)
  } else if (title.value == 'Tasks') {
    if (!all_activities.data?.tasks) return []
    return sortByModified(all_activities.data.tasks)
  } else if (title.value == 'Notes') {
    if (!all_activities.data?.notes) return []
    return sortByModified(all_activities.data.notes)
  } else if (title.value == 'Attachments') {
    if (!all_activities.data?.attachments) return []
    return sortByModified(all_activities.data.attachments)
  }

  _activities.forEach((activity) => {
    activity.icon = timelineIcon(activity.activity_type, activity.is_lead)

    if (
      activity.activity_type == 'incoming_call' ||
      activity.activity_type == 'outgoing_call' ||
      activity.activity_type == 'communication'
    )
      return

    update_activities_details(activity)

    if (activity.other_versions) {
      activity.show_others = false
      activity.other_versions.forEach((other_version) => {
        update_activities_details(other_version)
      })
    }
  })
  return sortByCreation(_activities, isNewestFirst.value)
})

function sortByCreation(list, newestFirst = false) {
  // Direction comes from the comparator operand order (like sortByModified),
  // not .reverse(). A consistent comparator keeps .sort() idempotent, so
  // sorting the reactive array in place doesn't re-trigger this computed.
  return list.sort((a, b) =>
    newestFirst
      ? new Date(b.creation) - new Date(a.creation)
      : new Date(a.creation) - new Date(b.creation),
  )
}
function sortByModified(list) {
  return list.sort((b, a) => new Date(a.modified) - new Date(b.modified))
}

function update_activities_details(activity) {
  activity.owner_name = getUser(activity.owner).full_name
  activity.type = ''
  activity.value = ''
  activity.to = ''

  if (activity.activity_type == 'creation') {
    activity.type = activity.data
  } else if (activity.activity_type == 'added') {
    activity.type = 'added'
    activity.value = 'as'
  } else if (activity.activity_type == 'removed') {
    activity.type = 'removed'
    activity.value = 'value'
  } else if (activity.activity_type == 'changed') {
    activity.type = 'changed'
    activity.value = 'from'
    activity.to = 'to'
  }
}

const top = computed(() => {
  if (['Activity', 'Emails', 'Comments'].includes(title.value)) {
    return '32.3%'
  }
  return '30%'
})

const emptyText = computed(() => {
  let text = 'No Activities Found'
  if (title.value == 'Emails') {
    text = 'No Emails Found'
  } else if (title.value == 'Comments') {
    text = 'No Comments Found'
  } else if (title.value == 'Data') {
    text = 'No Data Fields Added Yet'
  } else if (title.value == 'Calls') {
    text = 'No Call History'
  } else if (title.value == 'Notes') {
    text = 'No Notes Found'
  } else if (title.value == 'Tasks') {
    text = 'No Tasks Found'
  } else if (title.value == 'Attachments') {
    text = 'No Attachments Found'
  } else if (title.value == 'WhatsApp') {
    text = 'No WhatsApp Messages Found'
  } else if (title.value == 'Chatwoot') {
    text = 'No Chatwoot Conversations Found'
  }
  return text
})

const emptyTextDescription = computed(() => {
  let description =
    'There are no activities to display here. Go ahead and make some changes.'
  if (title.value == 'Emails') {
    description =
      'No emails found in your inbox. New messages will appear here soon.'
  } else if (title.value == 'Comments') {
    description = 'Be the first to add one.'
  } else if (title.value == 'Data') {
    description = 'No data fields have been added yet.'
  } else if (title.value == 'Calls') {
    description = 'No recent calls to display. Log a call or call someone now!'
  } else if (title.value == 'Notes') {
    description = 'Nothing here for now. Add a note to keep track of things.'
  } else if (title.value == 'Tasks') {
    description =
      'Nothing to do at the moment. Start organizing by adding one here.'
  } else if (title.value == 'Attachments') {
    description =
      'No files have been attached yet. Upload files to see them here.'
  } else if (title.value == 'WhatsApp') {
    description = 'Start a conversation now!'
  } else if (title.value == 'Chatwoot') {
    description =
      'No Chatwoot conversation was found for this contact. Conversations started on connected channels will appear here.'
  }
  return description
})

const emptyTextIcon = computed(() => {
  let icon = ActivityIcon
  if (title.value == 'Emails') {
    icon = EmailIcon
  } else if (title.value == 'Comments') {
    icon = CommentIcon
  } else if (title.value == 'Data') {
    icon = DetailsIcon
  } else if (title.value == 'Calls') {
    icon = PhoneIcon
  } else if (title.value == 'Notes') {
    icon = NoteIcon
  } else if (title.value == 'Tasks') {
    icon = TaskIcon
  } else if (title.value == 'Attachments') {
    icon = AttachmentIcon
  } else if (title.value == 'WhatsApp') {
    icon = WhatsAppIcon
  } else if (title.value == 'Chatwoot') {
    icon = ChatwootIcon
  }
  return h(icon, { class: 'text-ink-gray-4' })
})

function timelineIcon(activity_type, is_lead) {
  let icon
  switch (activity_type) {
    case 'creation':
      icon = is_lead ? LeadsIcon : DealsIcon
      break
    case 'deal':
      icon = DealsIcon
      break
    case 'comment':
      icon = CommentIcon
      break
    case 'event':
      icon = CalendarIcon
      break
    case 'incoming_call':
      icon = InboundCallIcon
      break
    case 'outgoing_call':
      icon = OutboundCallIcon
      break
    case 'attachment_log':
      icon = AttachmentIcon
      break
    default:
      icon = DotIcon
  }

  return markRaw(icon)
}

const emailBox = ref(null)
const whatsappBox = ref(null)
const chatwootBox = ref(null)

watch([reload, reload_email], ([reload_value, reload_email_value]) => {
  if (reload_value || reload_email_value) {
    all_activities.reload()
    _document.reload()
    reload.value = false
    reload_email.value = false
  }
})

function scroll(hash) {
  if (['tasks', 'notes', 'events'].includes(route.hash?.slice(1))) return
  setTimeout(() => {
    let el
    if (!hash) {
      let e = document.getElementsByClassName('activity')
      el = isNewestFirst.value ? e[0] : e[e.length - 1]
    } else {
      el = document.getElementById(hash)
    }
    if (el && !useElementVisibility(el).value) {
      el.scrollIntoView({ behavior: 'smooth' })
      el.focus()
    }
  }, 500)
}

defineExpose({ emailBox, all_activities, changeTabTo })
</script>
