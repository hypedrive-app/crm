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
            :placeholder="__('Welcome Message')"
          >
            <template #prefix>
              <span
                class="lucide-search h-4 w-4 text-ink-gray-4"
                aria-hidden="true"
              />
            </template>
          </TextInput>
          <Button
            :label="__('Create New Template')"
            variant="solid"
            @click="newWhatsappTemplate"
          >
            <template #prefix>
              <span class="lucide-plus h-4 w-4" aria-hidden="true" />
            </template>
          </Button>
        </div>
        <div
          v-if="filteredTemplates.length"
          class="mt-2 grid max-h-[560px] grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-3"
        >
          <div
            v-for="template in filteredTemplates"
            :key="template.name"
            class="flex h-56 cursor-pointer flex-col gap-2 rounded-lg border p-3 hover:bg-surface-gray-2"
            @click="selectTemplate(template)"
          >
            <div
              class="border-b pb-2 text-base-semibold truncate"
              :title="template.name"
            >
              {{ template.name }}
            </div>
            <TextEditor
              v-if="template.template"
              :content="template.template"
              :editable="false"
              editor-class="!prose-sm max-w-none !text-sm text-ink-gray-5 focus:outline-none"
              class="flex-1 overflow-hidden"
            />
          </div>
        </div>
        <div v-else class="mt-2">
          <div class="flex h-56 flex-col items-center justify-center">
            <div class="text-lg text-ink-gray-4">
              {{ __('No Templates Found') }}
            </div>
            <Button
              :label="__('Create New')"
              class="mt-4"
              @click="newWhatsappTemplate"
            />
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col gap-4">
        <div class="rounded-lg border p-3 text-sm text-ink-gray-6 whitespace-pre-line">
          {{ previewText }}
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
        <div class="flex justify-end gap-2">
          <Button :label="__('Back')" @click="selectedTemplate = null" />
          <Button
            :label="__('Send')"
            variant="solid"
            @click="confirmSend"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { TextEditor, createListResource, FormControl, ErrorMessage } from 'frappe-ui'
import { ref, computed, nextTick, watch, onMounted } from 'vue'

const props = defineProps({
  doctype: { type: String, default: '' },
})

const show = defineModel({ type: Boolean })
const searchInput = ref('')

const emit = defineEmits(['send'])

const search = ref('')
const selectedTemplate = ref(null)
const bodyParamValues = ref([])
const headerParamValues = ref([])
const validationError = ref('')

const templates = createListResource({
  type: 'list',
  doctype: 'WhatsApp Templates',
  cache: ['whatsappTemplates'],
  fields: [
    'name',
    'template',
    'footer',
    'header',
    'header_type',
    'sample_values',
  ],
  filters: { status: 'APPROVED', for_doctype: ['in', [props.doctype, '']] },
  orderBy: 'modified desc',
  pageLength: 99999,
})

onMounted(() => {
  if (templates.data == null) {
    templates.fetch()
  }
})

const filteredTemplates = computed(() => {
  return (
    templates.data?.filter((template) => {
      return template.name.toLowerCase().includes(search.value.toLowerCase())
    }) ?? []
  )
})

const modalTitle = computed(() =>
  selectedTemplate.value ? __('Fill Template Parameters') : __('WhatsApp Templates'),
)

// Count {{n}} style placeholders in a template string.
function countPlaceholders(text) {
  if (!text) return 0
  const matches = [...text.matchAll(/\{\{\s*(\d+)\s*\}\}/g)].map((m) => parseInt(m[1], 10))
  return matches.length ? Math.max(...matches) : 0
}

const bodyParamCount = computed(() => countPlaceholders(selectedTemplate.value?.template))
const headerParamCount = computed(() =>
  selectedTemplate.value?.header_type === 'TEXT'
    ? countPlaceholders(selectedTemplate.value?.header)
    : 0,
)

const bodySampleValues = computed(() =>
  selectedTemplate.value?.sample_values
    ? selectedTemplate.value.sample_values.split(',').map((v) => v.trim())
    : [],
)
const headerSampleValues = computed(() => [])

const previewText = computed(() => {
  let text = selectedTemplate.value?.template || ''
  bodyParamValues.value.forEach((val, idx) => {
    text = text.replaceAll(`{{${idx + 1}}}`, val || `{{${idx + 1}}}`)
  })
  return text
})

function selectTemplate(template) {
  selectedTemplate.value = template
  validationError.value = ''
  bodyParamValues.value = Array(countPlaceholders(template.template)).fill('')
  headerParamValues.value = Array(
    template.header_type === 'TEXT' ? countPlaceholders(template.header) : 0,
  ).fill('')

  // Pre-fill with sample values as a starting point so the agent only has
  // to edit, not type everything from scratch.
  const samples = template.sample_values ? template.sample_values.split(',').map((v) => v.trim()) : []
  bodyParamValues.value = bodyParamValues.value.map((_, idx) => samples[idx] || '')
}

function confirmSend() {
  if (bodyParamValues.value.some((v) => !v) || headerParamValues.value.some((v) => !v)) {
    validationError.value = __('Please fill in all template parameters before sending.')
    return
  }
  validationError.value = ''
  emit('send', {
    template: selectedTemplate.value.name,
    bodyParameters: bodyParamValues.value,
    headerParameters: headerParamValues.value,
  })
  selectedTemplate.value = null
}

function newWhatsappTemplate() {
  show.value = false
  window.open('/app/whatsapp-templates/new')
}

watch(show, (value) => {
  if (value) {
    selectedTemplate.value = null
    validationError.value = ''
    nextTick(() => searchInput.value?.el?.focus())
  }
})
</script>
