<template>
  <SettingsLayoutBase
    :title="__('WhatsApp Recipient Lists')"
    :description="
      __(
        'Reusable lists of phone numbers for bulk WhatsApp campaigns. Each recipient can optionally carry per-recipient values used when a template is sent with unique variables.',
      )
    "
  >
    <template #header-actions>
      <Button
        variant="solid"
        icon-left="lucide-plus"
        @click="openCreateDialog"
      >
        {{ __('New List') }}
      </Button>
    </template>
    <template #content>
      <div
        v-if="listsResource.loading && !listsResource.data"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
      <div
        v-else-if="!lists.length"
        class="relative flex h-full w-full justify-center"
      >
        <div
          class="absolute left-1/2 flex w-72 -translate-x-1/2 flex-col items-center gap-3"
          :style="{ top: '25%' }"
        >
          <WhatsAppIcon class="size-7.5 text-ink-gray-5" />
          <div class="flex flex-col items-center gap-1.5 text-center">
            <span class="text-lg-medium text-ink-gray-8">
              {{ __('No Recipient Lists Yet') }}
            </span>
            <span class="text-center text-p-base text-ink-gray-6">
              {{ __('Create a list of phone numbers to reuse across bulk WhatsApp campaigns.') }}
            </span>
            <Button variant="solid" @click="openCreateDialog">
              {{ __('New List') }}
            </Button>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col gap-3">
        <TextInput
          v-model="search"
          type="text"
          :placeholder="__('Search lists')"
          class="w-full sm:w-72"
        >
          <template #prefix>
            <span class="lucide-search h-4 w-4 text-ink-gray-4" aria-hidden="true" />
          </template>
        </TextInput>
        <div class="overflow-x-auto rounded-lg border border-outline-elevation-2">
          <table class="w-full min-w-[640px] text-left text-p-sm">
            <thead>
              <tr class="border-b border-outline-elevation-2 bg-surface-gray-1">
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('List Name') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Description') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Recipients') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Last Updated') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6" />
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="list in filteredLists"
                :key="list.name"
                class="border-b border-outline-elevation-2 last:border-b-0 hover:bg-surface-gray-1"
              >
                <td class="px-3 py-2 text-p-sm-medium text-ink-gray-8">
                  {{ list.list_name }}
                </td>
                <td class="px-3 py-2 text-ink-gray-6 max-w-[320px] truncate">
                  {{ list.description || '-' }}
                </td>
                <td class="px-3 py-2">
                  <Badge :label="String(list.recipient_count)" theme="gray" variant="subtle" />
                </td>
                <td class="px-3 py-2 whitespace-nowrap text-ink-gray-5">
                  {{ formatDate(list.modified) }}
                </td>
                <td class="px-3 py-2">
                  <Dropdown
                    placement="right"
                    :options="dropdownOptions(list)"
                    @click.stop
                  >
                    <Button icon="lucide-more-horizontal" variant="ghost" @click="resetDeleteConfirm" />
                  </Dropdown>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredLists.length" class="py-6 text-center text-p-sm text-ink-gray-5">
          {{ __('No lists match your search.') }}
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <Dialog v-model:open="dialog.show" :size="'2xl'" :title="dialog.isEdit ? __('Edit Recipient List') : __('New Recipient List')">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="dialog.list_name"
          type="text"
          :label="__('List Name')"
          required
        />
        <FormControl
          v-model="dialog.description"
          type="textarea"
          :label="__('Description')"
          :placeholder="__('Optional note about who this list is for')"
        />
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <span class="text-p-sm-medium text-ink-gray-7">{{ __('Recipients') }}</span>
            <span class="text-p-sm text-ink-gray-5">
              {{ __('{0} recipient(s)', [dialog.recipients.length]) }}
            </span>
          </div>
          <FormControl
            v-model="recipientsText"
            type="textarea"
            :rows="8"
            :placeholder="
              __(
                'One recipient per line: phone number, optional name\\n+919876543210, Priya Sharma\\n+14155552671',
              )
            "
            :description="
              __(
                'Enter one recipient per line as `phone number` or `phone number, name`. Include the country code.',
              )
            "
          />
        </div>
        <ErrorMessage :message="dialog.error" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="subtle" :label="__('Cancel')" @click="dialog.show = false" />
        <Button
          variant="solid"
          :label="dialog.isEdit ? __('Save') : __('Create')"
          :loading="saveResource.loading"
          @click="saveList"
        />
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import {
  Badge,
  Button,
  Dialog,
  Dropdown,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  TextInput,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { formatDate } from '@/utils'
import { ConfirmDelete } from '@/utils'

const search = ref('')
const deleteConfirmName = ref('')

function resetDeleteConfirm() {
  deleteConfirmName.value = ''
}

const listsResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_recipient_lists',
  cache: 'CRM WhatsApp Recipient Lists',
  auto: false,
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to load recipient lists'))
  },
})

const lists = computed(() => listsResource.data || [])

const filteredLists = computed(() => {
  if (!search.value) return lists.value
  const query = search.value.toLowerCase()
  return lists.value.filter((list) => {
    return (
      (list.list_name || '').toLowerCase().includes(query) ||
      (list.description || '').toLowerCase().includes(query)
    )
  })
})

const dialog = ref({
  show: false,
  isEdit: false,
  name: '',
  list_name: '',
  description: '',
  recipients: [],
  error: '',
})

const recipientsText = ref('')

// Keep dialog.recipients (the structured payload) in sync with the textarea
// the manager actually types into — parsing on every keystroke is cheap
// for the list sizes this UI targets and keeps the "N recipient(s)" counter
// live without a separate parse-on-save step that could silently diverge.
watch(recipientsText, (text) => {
  dialog.value.recipients = parseRecipients(text)
})

function parseRecipients(text) {
  if (!text) return []
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [mobile, ...rest] = line.split(',')
      return {
        mobile_number: (mobile || '').trim(),
        recipient_name: rest.join(',').trim() || undefined,
      }
    })
    .filter((row) => row.mobile_number)
}

function recipientsToText(recipients) {
  return (recipients || [])
    .map((r) => [r.mobile_number, r.recipient_name].filter(Boolean).join(', '))
    .join('\n')
}

function openCreateDialog() {
  dialog.value = {
    show: true,
    isEdit: false,
    name: '',
    list_name: '',
    description: '',
    recipients: [],
    error: '',
  }
  recipientsText.value = ''
}

const detailResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_recipient_list',
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to load recipient list'))
  },
})

function openEditDialog(list) {
  detailResource.submit(
    { name: list.name },
    {
      onSuccess(data) {
        dialog.value = {
          show: true,
          isEdit: true,
          name: data.name,
          list_name: data.list_name,
          description: data.description,
          recipients: data.recipients || [],
          error: '',
        }
        recipientsText.value = recipientsToText(data.recipients)
      },
    },
  )
}

// createResource() closes over its `options.url` at construction time —
// reassigning `.url` on the returned reactive object afterwards does not
// change what gets fetched (see frappe-ui's resources.js: the fetcher reads
// `options.url`, not `out.url`). So create/update need two distinct
// resources rather than one resource with a swapped-out url.
function onSaveSuccess() {
  toast.success(dialog.value.isEdit ? __('Recipient list updated') : __('Recipient list created'))
  dialog.value.show = false
  listsResource.reload()
}
function onSaveError(error) {
  dialog.value.error = error?.messages?.[0] || __('Failed to save recipient list')
}

const createListResource = createResource({
  url: 'crm.api.whatsapp.create_whatsapp_recipient_list',
  onSuccess: onSaveSuccess,
  onError: onSaveError,
})

const updateListResource = createResource({
  url: 'crm.api.whatsapp.update_whatsapp_recipient_list',
  onSuccess: onSaveSuccess,
  onError: onSaveError,
})

const saveResource = computed(() => (dialog.value.isEdit ? updateListResource : createListResource))

function saveList() {
  dialog.value.error = ''
  if (!dialog.value.list_name?.trim()) {
    dialog.value.error = __('List Name is required')
    return
  }
  if (!dialog.value.recipients.length) {
    dialog.value.error = __('Add at least one recipient')
    return
  }

  saveResource.value.submit({
    ...(dialog.value.isEdit ? { name: dialog.value.name } : {}),
    list_name: dialog.value.list_name,
    description: dialog.value.description,
    recipients: dialog.value.recipients,
  })
}

const deleteResource = createResource({
  url: 'crm.api.whatsapp.delete_whatsapp_recipient_list',
  onSuccess() {
    toast.success(__('Recipient list deleted'))
    resetDeleteConfirm()
    listsResource.reload()
  },
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to delete recipient list'))
    resetDeleteConfirm()
  },
})

function deleteList(list) {
  deleteResource.submit({ name: list.name })
}

function dropdownOptions(list) {
  const isConfirmingDelete = computed({
    get: () => deleteConfirmName.value === list.name,
    set: (val) => {
      deleteConfirmName.value = val ? list.name : ''
    },
  })
  return [
    {
      label: __('Edit'),
      icon: 'edit',
      onClick: () => openEditDialog(list),
      condition: () => !isConfirmingDelete.value,
    },
    ...ConfirmDelete({
      isConfirmingDelete,
      onConfirmDelete: () => deleteList(list),
    }),
  ]
}

onMounted(() => {
  listsResource.reload()
})
</script>
