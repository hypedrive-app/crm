<!-- eslint-disable vue/no-v-html -->
<template>
  <div
    v-if="reply?.message"
    class="flex items-center gap-2 px-3 pt-2 sm:px-10"
  >
    <div
      class="mb-1 min-w-0 flex-1 cursor-pointer rounded border-0 border-l-4 bg-surface-gray-2 p-2 text-base text-ink-gray-5"
      :class="
        reply.type == 'Incoming'
          ? 'border-outline-green-3'
          : 'border-outline-blue-3'
      "
    >
      <div
        class="mb-1 text-sm-bold"
        :class="
          reply.type == 'Incoming' ? 'text-ink-green-5' : 'text-ink-blue-link'
        "
      >
        {{ reply.from_name || __('You') }}
      </div>
      <div
        class="max-h-12 overflow-hidden"
        v-html="sanitizeHTML(reply.message)"
      />
    </div>

    <Button variant="ghost" icon="lucide-x" @click="reply = {}" />
  </div>
  <!-- Meta's 24h customer-service window has closed: a free-form message would
       be rejected by Meta after a pointless round-trip, so lock the composer and
       steer the agent to a template (the only thing that reopens the window),
       mirroring the Chatwoot tab's out-of-window panel. -->
  <div
    v-if="!canReply"
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
            'This conversation is outside the 24-hour reply window. The customer needs to message first, or send a template message to reopen it.',
          )
        }}
      </span>
    </div>
    <div class="flex flex-wrap items-center gap-2 self-end">
      <Button variant="solid" @click="emit('sendTemplate')">
        {{ __('Send Template') }}
      </Button>
    </div>
  </div>
  <div v-else class="flex items-end gap-2 px-3 py-2.5 sm:px-10" v-bind="$attrs">
    <div class="flex h-8 items-center gap-1">
      <FileUploader @success="(file) => uploadFile(file)">
        <template #default="{ openFileSelector }">
          <Dropdown :options="uploadOptions(openFileSelector)">
            <Tooltip :text="__('Attach')">
              <button
                type="button"
                :aria-label="__('Attach a file')"
                class="flex size-7 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-7"
              >
                <span class="lucide-plus size-4.5" aria-hidden="true" />
              </button>
            </Tooltip>
          </Dropdown>
        </template>
      </FileUploader>
      <IconPicker
        v-slot="{ togglePopover }"
        v-model="emoji"
        @update:modelValue="
          () => {
            content += emoji
            $refs.textareaRef.el.focus()
            capture('whatsapp_emoji_added')
          }
        "
      >
        <Tooltip :text="__('Emoji')">
          <button
            type="button"
            :aria-label="__('Add emoji')"
            class="flex size-7 items-center justify-center rounded text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-7"
            @click="togglePopover"
          >
            <SmileIcon class="size-4.5" />
          </button>
        </Tooltip>
      </IconPicker>
    </div>
    <Textarea
      ref="textareaRef"
      v-model="content"
      type="textarea"
      class="min-h-8 w-full"
      :rows="rows"
      :placeholder="placeholder"
      @focus="onComposerFocus"
      @blur="onComposerBlur"
      @keydown="onKeydown"
      @compositionstart="isComposing = true"
      @compositionend="isComposing = false"
    />
    <Button
      variant="solid"
      class="shrink-0"
      :loading="sending"
      :disabled="(!content.trim() && !whatsapp.attach) || sending"
      @click="sendTextMessage()"
    >
      {{ __('Send') }}
    </Button>
  </div>
</template>

<script setup>
import IconPicker from '@/components/IconPicker.vue'
import SmileIcon from '@/components/Icons/SmileIcon.vue'
import { sanitizeHTML } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import {
  Button,
  createResource,
  Textarea,
  Tooltip,
  FileUploader,
  Dropdown,
  toast,
} from 'frappe-ui'
import { computed, ref, nextTick, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, default: '' },
  // Whether Meta's 24h free-form reply window is currently open. When false the
  // composer is swapped for a "send a template to reopen" panel. Defaults true
  // so a slow window fetch never gratuitously locks the box.
  canReply: { type: Boolean, default: true },
})

const emit = defineEmits(['sendTemplate'])

const doc = defineModel({ type: Object, default: () => ({}) })
const whatsapp = defineModel('whatsapp', { type: Object, default: () => ({}) })
const reply = defineModel('reply', { type: Object, default: () => ({}) })

const { capture } = useTelemetry()

const textareaRef = ref(null)
const emoji = ref('')
const sending = ref(false)
const focused = ref(false)

const content = ref('')
const placeholder = ref(__('Type your message here...'))
const fileType = ref('')

// Auto-grow the composer to its content instead of jumping to a fixed 6 rows on
// focus (a big empty box) and snapping back to 1 on blur (which clipped a
// multi-line draft out of sight). Grows 1→6 with the number of lines typed;
// while focused it keeps at least 2 rows so there's room to type.
const rows = computed(() => {
  const lines = content.value ? content.value.split('\n').length : 1
  const min = focused.value ? 2 : 1
  return Math.min(6, Math.max(min, lines))
})

function onComposerFocus() {
  focused.value = true
}

function onComposerBlur() {
  focused.value = false
}

function show() {
  nextTick(() => textareaRef.value.el.focus())
}

function uploadFile(file) {
  whatsapp.value.attach = file.file_url
  whatsapp.value.content_type = fileType.value
  sendWhatsAppMessage()
  capture('whatsapp_upload_file')
}

// IME composition guard: while an IME (Hindi/Japanese/Chinese input, or an
// emoji-picker candidate list) is composing, the Enter keystroke that commits
// the candidate also fires as a normal 'Enter' keydown. Treating that as "send"
// swallows the user's half-composed text and sends garbage — so both the
// browser's own `event.isComposing` and the legacy keyCode 229 fallback (older
// Safari and some Android WebViews don't set isComposing reliably) are checked
// before Enter is ever treated as submit. Mirrors ChatwootBox exactly.
const isComposing = ref(false)

function isComposingEvent(event) {
  return isComposing.value || event.isComposing || event.keyCode === 229
}

function onKeydown(event) {
  if (event.key !== 'Enter') return
  if (isComposingEvent(event)) return
  if (event.shiftKey) return // Shift+Enter = newline, never sends
  event.preventDefault()
  event.stopPropagation()
  sendTextMessage()
}

function sendTextMessage() {
  // An empty send used to be reachable via Enter on a blank composer, which
  // posted a message with no body.
  if (!content.value.trim() && !whatsapp.value.attach) return
  // Belt-and-braces: the composer is normally swapped out when canReply is
  // false, but Enter can still fire from a stale render, and a free-form send
  // outside the window is guaranteed to be rejected by Meta. Fail loudly and
  // keep the text rather than posting a message that silently ends up failed.
  if (!props.canReply) {
    toast.error(
      __('Outside the 24-hour reply window — send a template message instead.'),
    )
    return
  }
  sendWhatsAppMessage()
  textareaRef.value?.el?.blur()
  capture('whatsapp_send_message')
}

async function sendWhatsAppMessage() {
  const args = {
    reference_doctype: props.doctype,
    reference_name: doc.value.name,
    message: content.value,
    to: doc.value.mobile_no,
    attach: whatsapp.value.attach || '',
    reply_to: reply.value?.name || '',
    content_type: whatsapp.value.content_type,
  }

  // Snapshot what the composer is about to lose, so a failed send can hand the
  // user's own text back instead of discarding it. The optimistic clear stays —
  // it keeps the composer responsive — but it is now reversible.
  const previous = {
    content: content.value,
    attach: whatsapp.value.attach,
    contentType: whatsapp.value.content_type,
    fileType: fileType.value,
    reply: reply.value,
  }

  content.value = ''
  fileType.value = ''
  whatsapp.value.attach = ''
  whatsapp.value.content_type = 'text'
  reply.value = {}
  sending.value = true

  createResource({
    url: 'crm.api.whatsapp.create_whatsapp_message',
    params: args,
    auto: true,
    onSuccess: () => {
      sending.value = false
      whatsapp.value.reload()
    },
    onError: (error) => {
      // Restore the composer so the user's text/attachment isn't lost, and
      // clear the in-flight state so the Send button never gets stuck spinning.
      sending.value = false
      content.value = previous.content
      whatsapp.value.attach = previous.attach
      whatsapp.value.content_type = previous.contentType
      fileType.value = previous.fileType
      reply.value = previous.reply
      toast.error(error.messages?.[0] || __('Failed to send WhatsApp message'))
    },
  })
}

function uploadOptions(openFileSelector) {
  return [
    {
      label: __('Upload Document'),
      icon: 'file',
      onClick: () => {
        fileType.value = 'document'
        openFileSelector()
      },
    },
    {
      label: __('Upload Image'),
      icon: 'image',
      onClick: () => {
        fileType.value = 'image'
        openFileSelector('image/*')
      },
    },
    {
      label: __('Upload Video'),
      icon: 'video',
      onClick: () => {
        fileType.value = 'video'
        openFileSelector('video/*')
      },
    },
    {
      label: __('Upload Audio'),
      icon: 'mic',
      onClick: () => {
        fileType.value = 'audio'
        openFileSelector('audio/*')
      },
    },
  ]
}

watch(reply, (value) => {
  if (value?.message) {
    show()
  }
})

defineExpose({ show })
</script>
