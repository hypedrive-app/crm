<template>
  <Dialog v-model:open="show" :title="modalTitle" :size="'4xl'">
    <template #default>
      <div v-if="!selectedTemplate">
        <div class="w-full flex items-center gap-2">
          <TextInput
            ref="searchInput"
            v-model="search"
            class="w-full"
            type="text"
            :placeholder="__('Search templates by name or content...')"
          >
            <template #prefix>
              <span
                class="lucide-search h-4 w-4 text-ink-gray-4"
                aria-hidden="true"
              />
            </template>
          </TextInput>
        </div>
        <div
          v-if="templates.loading"
          class="mt-2 flex h-56 items-center justify-center"
        >
          <LoadingIndicator class="size-6" />
        </div>
        <div
          v-else-if="filteredTemplates.length"
          class="mt-2 grid max-h-[560px] grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-3"
        >
<!-- min-h (not fixed h-56) so short cards shrink; line-clamp still caps long bodies. -->
          <div
            v-for="template in filteredTemplates"
            :key="`${template.name}-${template.language}`"
            class="flex min-h-56 cursor-pointer flex-col gap-2 rounded-lg border border-outline-gray-2 p-3 hover:bg-surface-gray-2"
            @click="selectTemplate(template)"
          >
            <!-- border-outline-gray-2: bare `border-b` is not theme-aware. -->
            <div class="flex items-start justify-between gap-2 border-b border-outline-gray-2 pb-2">
              <div
                class="text-base-semibold truncate"
                :title="template.name"
              >
                {{ template.name }}
              </div>
              <div
                class="shrink-0 rounded bg-surface-gray-2 px-1.5 py-0.5 text-2xs text-ink-gray-6"
              >
                {{ template.category }}
              </div>
            </div>
            <div class="flex-1 overflow-hidden text-p-sm text-ink-gray-6 line-clamp-6 whitespace-pre-line">
              {{ bodyText(template) }}
            </div>
          </div>
        </div>
        <div v-else class="mt-2">
          <div class="flex h-56 flex-col items-center justify-center">
            <div class="text-lg text-ink-gray-4">
              {{ __('No Templates Found') }}
            </div>
            <div class="mt-1 text-p-sm text-ink-gray-5">
              {{
                __(
                  'Approved WhatsApp templates synced to Chatwoot will appear here.',
                )
              }}
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col gap-4">
        <div class="rounded-lg border border-outline-gray-2 p-3 text-sm text-ink-gray-6">
          <!-- Media headers (IMAGE/VIDEO/DOCUMENT/LOCATION) carry no text, so show a
               placeholder chip — otherwise the agent sends blind, unaware a media header exists. -->
          <div
            v-if="mediaHeaderLabel"
            class="mb-2 inline-flex w-fit items-center gap-1 rounded bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-6"
          >
            {{ mediaHeaderLabel }}
          </div>
          <div
            v-if="headerText"
            class="mb-2 border-b border-outline-gray-2 pb-2 text-sm-semibold text-ink-gray-8 whitespace-pre-line"
          >
            {{ renderedHeader }}
          </div>
          <div class="whitespace-pre-line">{{ renderedBody }}</div>
          <div
            v-if="footerText"
            class="mt-2 border-t border-outline-gray-2 pt-2 text-xs text-ink-gray-5 whitespace-pre-line"
          >
            {{ footerText }}
          </div>
          <!-- Preview template buttons as disabled chips so the agent knows what
               CTAs/quick-replies the recipient will see. -->
          <div
            v-if="templateButtons.length"
            class="mt-2 flex flex-wrap gap-1.5 border-t border-outline-gray-2 pt-2"
          >
            <span
              v-for="(btn, i) in templateButtons"
              :key="'btn-' + i"
              class="rounded border border-outline-gray-2 px-2 py-0.5 text-xs text-ink-gray-5"
            >
              {{ btn }}
            </span>
          </div>
        </div>
        <div
          v-if="headerParamCount > 0"
          class="flex flex-col gap-2"
        >
          <div class="text-sm-medium text-ink-gray-6">
            {{ __('Header Parameters') }}
          </div>
          <FormControl
            v-for="i in headerParamCount"
            :key="'header-' + i"
            :label="__('Parameter {0}', [i])"
            v-model="headerParamValues[i - 1]"
            type="text"
            :placeholder="headerSampleValues[i - 1] || ''"
          />
        </div>
        <div
          v-if="bodyParamCount > 0"
          class="flex flex-col gap-2"
        >
          <div class="text-sm-medium text-ink-gray-6">
            {{ __('Body Parameters') }}
          </div>
          <FormControl
            v-for="i in bodyParamCount"
            :key="'body-' + i"
            :label="__('Parameter {0}', [i])"
            v-model="bodyParamValues[i - 1]"
            type="text"
            :placeholder="bodySampleValues[i - 1] || ''"
          />
        </div>
        <div
          v-if="!bodyParamCount && !headerParamCount"
          class="text-sm text-ink-gray-5"
        >
          {{ __('This template has no parameters.') }}
        </div>
        <ErrorMessage :message="validationError" />
      </div>
    </template>
    <!-- Actions belong in the Dialog #actions slot (repo standard), not hand-rolled
         inside #default. Only shown on the fill-parameters step. -->
    <template v-if="selectedTemplate" #actions>
      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button
          class="w-full sm:w-auto"
          variant="subtle"
          :label="__('Back')"
          :disabled="sending"
          @click="selectedTemplate = null"
        />
        <Button
          class="w-full sm:w-auto"
          :label="__('Send')"
          variant="solid"
          :loading="sending"
          :disabled="!allParamsFilled"
          @click="confirmSend"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { FormControl, ErrorMessage, LoadingIndicator, createResource } from 'frappe-ui'
import { ref, computed, nextTick, watch } from 'vue'

const show = defineModel({ type: Boolean })
const searchInput = ref('')

const emit = defineEmits(['send'])

const search = ref('')
const selectedTemplate = ref(null)
const bodyParamValues = ref([])
const headerParamValues = ref([])
const validationError = ref('')
const sending = ref(false)

const templates = createResource({
  url: 'crm.api.chatwoot.get_chatwoot_templates',
  cache: 'chatwoot_templates',
  auto: false,
})

const filteredTemplates = computed(() => {
  const query = search.value.toLowerCase()
  return (
    templates.data?.filter((template) => {
      return (
        template.name.toLowerCase().includes(query) ||
        bodyText(template).toLowerCase().includes(query)
      )
    }) ?? []
  )
})

const modalTitle = computed(() =>
  selectedTemplate.value ? __('Fill Template Parameters') : __('WhatsApp Templates'),
)

// Chatwoot's inbox.message_templates array mirrors Meta's own WhatsApp
// Business API "components" shape verbatim: an array of
// { type: 'HEADER'|'BODY'|'FOOTER'|'BUTTONS', format, text, example }.
function findComponent(template, type) {
  return template?.components?.find((c) => c.type === type)
}

function bodyText(template) {
  return findComponent(template, 'BODY')?.text || ''
}

function headerComponent(template) {
  return findComponent(template, 'HEADER')
}

function footerTextOf(template) {
  return findComponent(template, 'FOOTER')?.text || ''
}

// Count {{n}} style placeholders in a template string.
function countPlaceholders(text) {
  if (!text) return 0
  const matches = [...text.matchAll(/\{\{\s*(\d+)\s*\}\}/g)].map((m) => parseInt(m[1], 10))
  return matches.length ? Math.max(...matches) : 0
}

const bodyParamCount = computed(() => countPlaceholders(bodyText(selectedTemplate.value)))
const headerParamCount = computed(() => {
  const header = headerComponent(selectedTemplate.value)
  if (!header || header.format !== 'TEXT') return 0
  return countPlaceholders(header.text)
})

function sampleValuesOf(component) {
  // Meta's example shape: { body_text: [[...]] } or { header_text: [...] }
  const bodyExamples = component?.example?.body_text
  if (Array.isArray(bodyExamples) && Array.isArray(bodyExamples[0])) {
    return bodyExamples[0]
  }
  const headerExamples = component?.example?.header_text
  if (Array.isArray(headerExamples)) {
    return headerExamples
  }
  return []
}

const bodySampleValues = computed(() =>
  sampleValuesOf(findComponent(selectedTemplate.value, 'BODY')),
)
const headerSampleValues = computed(() =>
  sampleValuesOf(headerComponent(selectedTemplate.value)),
)

const headerText = computed(() => headerComponent(selectedTemplate.value)?.text || '')
const footerText = computed(() => footerTextOf(selectedTemplate.value))

// Non-TEXT headers (IMAGE/VIDEO/DOCUMENT/LOCATION) carry no text — surface them as a
// labelled chip so the agent isn't sending a media template blind.
const MEDIA_HEADER_LABELS = {
  IMAGE: '📷 ' + __('Image header'),
  VIDEO: '🎬 ' + __('Video header'),
  DOCUMENT: '📄 ' + __('Document header'),
  LOCATION: '📍 ' + __('Location header'),
}
const mediaHeaderLabel = computed(() => {
  const format = headerComponent(selectedTemplate.value)?.format
  return format && format !== 'TEXT' ? MEDIA_HEADER_LABELS[format] || '' : ''
})

// Button titles from the BUTTONS component, previewed as read-only chips.
const templateButtons = computed(() => {
  const buttons = findComponent(selectedTemplate.value, 'BUTTONS')?.buttons
  if (!Array.isArray(buttons)) return []
  return buttons.map((b) => b.text || b.title || '').filter(Boolean)
})

// Gate Send until every placeholder is filled — Meta rejects param-count mismatches
// (#132000), so validating client-side avoids a blind failed send.
const allParamsFilled = computed(
  () =>
    bodyParamValues.value.every((v) => v && v.trim()) &&
    headerParamValues.value.every((v) => v && v.trim()),
)

function renderWithParams(text, values) {
  let rendered = text || ''
  values.forEach((val, idx) => {
    rendered = rendered.replaceAll(`{{${idx + 1}}}`, val || `{{${idx + 1}}}`)
  })
  return rendered
}

const renderedBody = computed(() =>
  renderWithParams(bodyText(selectedTemplate.value), bodyParamValues.value),
)
const renderedHeader = computed(() =>
  renderWithParams(headerText.value, headerParamValues.value),
)

function selectTemplate(template) {
  selectedTemplate.value = template
  validationError.value = ''
  bodyParamValues.value = Array(countPlaceholders(bodyText(template))).fill('')
  const header = headerComponent(template)
  headerParamValues.value = Array(
    header?.format === 'TEXT' ? countPlaceholders(header.text) : 0,
  ).fill('')

  // Pre-fill with Meta's own sample values as a starting point so the agent
  // only has to edit, not type everything from scratch.
  const samples = sampleValuesOf(findComponent(template, 'BODY'))
  bodyParamValues.value = bodyParamValues.value.map((_, idx) => samples[idx] || '')
  const headerSamples = sampleValuesOf(header)
  headerParamValues.value = headerParamValues.value.map((_, idx) => headerSamples[idx] || '')
}

function confirmSend() {
  if (!allParamsFilled.value) {
    validationError.value = __('Please fill in all template parameters before sending.')
    return
  }
  validationError.value = ''

  const processedParams = {}
  bodyParamValues.value.forEach((val, idx) => {
    processedParams[String(idx + 1)] = val
  })

  emit('send', {
    templateName: selectedTemplate.value.name,
    category: selectedTemplate.value.category,
    language: selectedTemplate.value.language,
    processedParams,
  })
}

function setSending(value) {
  sending.value = value
}

function setError(message) {
  validationError.value = message
}

function closeAfterSuccess() {
  selectedTemplate.value = null
  show.value = false
}

defineExpose({ setSending, setError, closeAfterSuccess })

watch(show, (value) => {
  if (value) {
    selectedTemplate.value = null
    validationError.value = ''
    sending.value = false
    if (templates.data == null) {
      templates.fetch()
    }
    nextTick(() => searchInput.value?.el?.focus())
  }
})
</script>
