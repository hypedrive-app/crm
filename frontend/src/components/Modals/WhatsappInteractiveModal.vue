<template>
  <Dialog v-model:open="show" :title="__('Send Interactive Message')" :size="'2xl'">
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="interactiveType"
          type="select"
          size="md"
          :label="__('Type')"
          :options="[
            { label: __('Quick-reply Buttons'), value: 'button' },
            { label: __('List Menu'), value: 'list' },
          ]"
        />

        <FormControl
          v-model="message"
          type="textarea"
          size="md"
          :label="__('Message')"
          :rows="3"
          :placeholder="__('Choose an option below:')"
          :required="true"
        />

        <!-- Quick-reply buttons -->
        <div v-if="interactiveType == 'button'" class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <div class="text-sm-medium text-ink-gray-6">
              {{ __('Buttons') }}
              <span class="text-ink-gray-4">({{ buttons.length }}/3)</span>
            </div>
            <Button
              v-if="buttons.length < 3"
              variant="ghost"
              :label="__('Add Button')"
              icon-left="lucide-plus"
              @click="addButton"
            />
          </div>
          <div
            v-for="(button, index) in buttons"
            :key="button.id"
            class="flex items-center gap-2"
          >
            <TextInput
              v-model="button.title"
              class="flex-1"
              :placeholder="__('Button {0} label', [index + 1])"
              :maxlength="20"
            />
            <Button
              variant="ghost"
              icon="lucide-x"
              :aria-label="__('Remove button {0}', [index + 1])"
              @click="removeButton(index)"
            />
          </div>
          <div v-if="!buttons.length" class="text-sm text-ink-gray-5">
            {{ __('Add up to 3 quick-reply buttons.') }}
          </div>
        </div>

        <!-- List menu -->
        <div v-else class="flex flex-col gap-3">
          <FormControl
            v-model="listButtonLabel"
            size="md"
            :label="__('Menu Button Label')"
            :placeholder="__('Select Option')"
            :maxlength="20"
          />

          <div class="flex items-center justify-between">
            <div class="text-sm-medium text-ink-gray-6">
              {{ __('Sections') }}
              <span class="text-ink-gray-4">({{ totalRows }}/10 options)</span>
            </div>
            <Button
              variant="ghost"
              :label="__('Add Section')"
              icon-left="lucide-plus"
              @click="addSection"
            />
          </div>

          <div
            v-for="(section, sectionIndex) in sections"
            :key="section.id"
            class="flex flex-col gap-2 rounded-md border border-outline-gray-2 p-3"
          >
            <div class="flex items-center gap-2">
              <TextInput
                v-model="section.title"
                class="flex-1"
                :placeholder="__('Section title')"
              />
              <Button
                v-if="sections.length > 1"
                variant="ghost"
                icon="lucide-x"
                :aria-label="__('Remove section {0}', [sectionIndex + 1])"
                @click="removeSection(sectionIndex)"
              />
            </div>
            <div
              v-for="(row, rowIndex) in section.rows"
              :key="row.id"
              class="ml-4 flex flex-col gap-1 rounded-md bg-surface-gray-1 p-2"
            >
              <div class="flex items-center gap-2">
                <TextInput
                  v-model="row.title"
                  class="flex-1"
                  :placeholder="__('Option title')"
                />
                <Button
                  variant="ghost"
                  icon="lucide-x"
                  :aria-label="__('Remove option {0}', [rowIndex + 1])"
                  @click="removeRow(sectionIndex, rowIndex)"
                />
              </div>
              <TextInput
                v-model="row.description"
                :placeholder="__('Description (optional)')"
              />
            </div>
            <Button
              v-if="totalRows < 10"
              variant="ghost"
              class="ml-4 !justify-start"
              :label="__('Add Option')"
              icon-left="lucide-plus"
              @click="addRow(sectionIndex)"
            />
          </div>
        </div>

        <ErrorMessage :message="validationError" />
      </div>
    </template>
    <!-- Actions in the Dialog #actions slot (repo standard); Cancel subtle,
         full-width stacked on mobile. -->
    <template #actions>
      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button
          class="w-full sm:w-auto"
          variant="subtle"
          :label="__('Cancel')"
          @click="show = false"
        />
        <Button
          class="w-full sm:w-auto"
          :label="__('Send')"
          variant="solid"
          :loading="sending"
          @click="confirmSend"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Dialog, FormControl, TextInput, ErrorMessage } from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const show = defineModel({ type: Boolean })
const emit = defineEmits(['send'])

defineProps({
  sending: { type: Boolean, default: false },
})

const interactiveType = ref('button')
const message = ref('')
const validationError = ref('')

const buttons = ref([])
const listButtonLabel = ref('')
const sections = ref([])

function newId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`
}

function addButton() {
  if (buttons.value.length >= 3) return
  buttons.value.push({ id: newId('btn'), title: '' })
}

function removeButton(index) {
  buttons.value.splice(index, 1)
}

function addSection() {
  sections.value.push({
    id: newId('section'),
    title: '',
    rows: [{ id: newId('row'), title: '', description: '' }],
  })
}

function removeSection(index) {
  sections.value.splice(index, 1)
}

function addRow(sectionIndex) {
  if (totalRows.value >= 10) return
  sections.value[sectionIndex].rows.push({
    id: newId('row'),
    title: '',
    description: '',
  })
}

function removeRow(sectionIndex, rowIndex) {
  sections.value[sectionIndex].rows.splice(rowIndex, 1)
}

const totalRows = computed(() =>
  sections.value.reduce((sum, section) => sum + section.rows.length, 0),
)

function resetForm() {
  interactiveType.value = 'button'
  message.value = ''
  validationError.value = ''
  buttons.value = [{ id: newId('btn'), title: '' }]
  listButtonLabel.value = ''
  sections.value = [
    {
      id: newId('section'),
      title: '',
      rows: [{ id: newId('row'), title: '', description: '' }],
    },
  ]
}

watch(show, (value) => {
  if (value) resetForm()
})

function confirmSend() {
  if (!message.value?.trim()) {
    validationError.value = __('Please enter a message body.')
    return
  }

  if (interactiveType.value == 'button') {
    const filled = buttons.value.filter((b) => b.title?.trim())
    if (!filled.length) {
      validationError.value = __('Please add at least one button.')
      return
    }
    validationError.value = ''
    emit('send', {
      interactiveType: 'button',
      message: message.value.trim(),
      buttons: filled.map((b) => ({ id: b.id, title: b.title.trim() })),
    })
    return
  }

  // List menu
  const cleanedSections = sections.value
    .map((section) => ({
      title: section.title?.trim() || '',
      rows: section.rows.filter((row) => row.title?.trim()),
    }))
    .filter((section) => section.title && section.rows.length)

  if (!cleanedSections.length) {
    validationError.value = __(
      'Please add at least one section with a title and one option.',
    )
    return
  }

  validationError.value = ''
  emit('send', {
    interactiveType: 'list',
    message: message.value.trim(),
    listButtonLabel: listButtonLabel.value?.trim() || '',
    sections: cleanedSections.map((section) => ({
      title: section.title,
      rows: section.rows.map((row) => ({
        id: row.id,
        title: row.title.trim(),
        description: row.description?.trim() || '',
      })),
    })),
  })
}

defineExpose({ resetForm })
</script>
