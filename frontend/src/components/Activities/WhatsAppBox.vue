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
  <div class="flex items-end gap-2 px-3 py-2.5 sm:px-10" v-bind="$attrs">
    <div class="flex h-8 items-center gap-2">
      <FileUploader @success="(file) => uploadFile(file)">
        <template #default="{ openFileSelector }">
          <div class="flex items-center space-x-2">
            <Dropdown :options="uploadOptions(openFileSelector)">
              <span
                class="lucide-plus size-4.5 cursor-pointer text-ink-gray-5"
                aria-hidden="true"
              />
            </Dropdown>
          </div>
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
        <SmileIcon
          class="flex size-4.5 cursor-pointer rounded-sm text-2xl leading-none text-ink-gray-4"
          @click="togglePopover"
        />
      </IconPicker>
    </div>
    <Textarea
      ref="textareaRef"
      v-model="content"
      type="textarea"
      class="min-h-8 w-full"
      :rows="rows"
      :placeholder="placeholder"
      @focus="rows = 6"
      @blur="rows = 1"
      @keydown="onKeydown"
      @compositionstart="isComposing = true"
      @compositionend="isComposing = false"
    />
    <Button
      variant="solid"
      class="shrink-0"
      :disabled="!content.trim() && !whatsapp.attach"
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
  FileUploader,
  Dropdown,
  toast,
} from 'frappe-ui'
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, default: '' },
})

const doc = defineModel({ type: Object, default: () => ({}) })
const whatsapp = defineModel('whatsapp', { type: Object, default: () => ({}) })
const reply = defineModel('reply', { type: Object, default: () => ({}) })

const { capture } = useTelemetry()

const rows = ref(1)
const textareaRef = ref(null)
const emoji = ref('')

const content = ref('')
const placeholder = ref(__('Type your message here...'))
const fileType = ref('')

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

  createResource({
    url: 'crm.api.whatsapp.create_whatsapp_message',
    params: args,
    auto: true,
    onSuccess: () => whatsapp.value.reload(),
    onError: (error) => {
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
