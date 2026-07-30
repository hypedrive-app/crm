<template>
  <SettingsLayoutBase
    :title="__('WhatsApp Bulk Campaigns')"
    :description="
      __(
        'Send an approved WhatsApp template to an entire recipient list in one go, and track delivery progress here.',
      )
    "
  >
    <template #header-actions>
      <Button
        variant="solid"
        icon-left="lucide-send"
        @click="openCreateDialog"
      >
        {{ __('New Campaign') }}
      </Button>
    </template>
    <template #content>
      <div
        v-if="campaignsResource.loading && !campaignsResource.data"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
      <div
        v-else-if="!campaigns.length"
        class="relative flex h-full w-full justify-center"
      >
        <div
          class="absolute left-1/2 flex w-72 -translate-x-1/2 flex-col items-center gap-3"
          :style="{ top: '25%' }"
        >
          <WhatsAppIcon class="size-7.5 text-ink-gray-5" />
          <div class="flex flex-col items-center gap-1.5 text-center">
            <span class="text-lg-medium text-ink-gray-8">
              {{ __('No Bulk Campaigns Yet') }}
            </span>
            <span class="text-center text-p-base text-ink-gray-6">
              {{ __('Send an approved template to a recipient list to reach many contacts at once.') }}
            </span>
            <Button variant="solid" @click="openCreateDialog">
              {{ __('New Campaign') }}
            </Button>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col gap-3">
        <div class="overflow-x-auto rounded-lg border border-outline-elevation-2">
          <table class="w-full min-w-[760px] text-left text-p-sm">
            <thead>
              <tr class="border-b border-outline-elevation-2 bg-surface-gray-1">
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Campaign') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Template') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Recipients') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Progress') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Status') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">{{ __('Sent') }}</th>
                <th class="px-3 py-2 font-medium text-ink-gray-6" />
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in campaigns"
                :key="c.name"
                class="border-b border-outline-elevation-2 last:border-b-0 align-top hover:bg-surface-gray-1"
              >
                <td class="px-3 py-2">
                  <div class="text-p-sm-medium text-ink-gray-8">{{ c.title || c.name }}</div>
                  <div class="text-xs text-ink-gray-5">{{ c.name }}</div>
                </td>
                <td class="px-3 py-2 text-ink-gray-6">{{ c.template || '-' }}</td>
                <td class="px-3 py-2 text-ink-gray-6">
                  {{ c.recipient_count || 0 }}
                </td>
                <td class="px-3 py-2 min-w-[140px]">
                  <div class="flex items-center gap-2">
                    <div class="h-1.5 flex-1 rounded-full bg-surface-gray-2 overflow-hidden">
                      <div
                        class="h-full rounded-full bg-surface-gray-7"
                        :style="{ width: progressPercent(c) + '%' }"
                      />
                    </div>
                    <span class="text-xs text-ink-gray-5 whitespace-nowrap">
                      {{ c.sent_count || 0 }}/{{ c.recipient_count || 0 }}
                    </span>
                  </div>
                </td>
                <td class="px-3 py-2">
                  <Badge :label="c.status || __('Draft')" :theme="statusTheme(c.status)" variant="subtle" />
                </td>
                <td class="px-3 py-2 whitespace-nowrap text-ink-gray-5">
                  {{ formatDate(c.modified) }}
                </td>
                <td class="px-3 py-2">
                  <Button
                    v-if="c.status === 'Partially Failed'"
                    variant="outline"
                    :label="__('Retry Failed')"
                    :loading="retryResource.loading && retryingName === c.name"
                    @click="retryFailed(c)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <Dialog v-model:open="dialog.show" :size="'2xl'" :title="__('New Bulk WhatsApp Campaign')">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="dialog.title"
          type="text"
          :label="__('Campaign Title')"
          required
        />
        <FormControl
          v-model="dialog.recipient_list"
          type="select"
          :label="__('Recipient List')"
          :options="recipientListOptions"
          required
        />
        <div v-if="selectedRecipientList" class="text-xs text-ink-gray-5 -mt-2">
          {{ __('{0} recipient(s) in this list', [selectedRecipientList.recipient_count]) }}
        </div>
        <FormControl
          v-model="dialog.template"
          type="select"
          :label="__('WhatsApp Template')"
          :options="templateOptions"
          required
        />
        <div v-if="selectedTemplate" class="rounded-lg border border-outline-elevation-2 p-3 text-p-sm text-ink-gray-6 whitespace-pre-line">
          {{ selectedTemplate.template }}
        </div>
        <div v-if="bodyParamCount > 0" class="flex flex-col gap-2">
          <div class="text-p-sm-medium text-ink-gray-7">
            {{ __('Template Parameters') }}
          </div>
          <p class="text-xs text-ink-gray-5">
            {{
              __(
                'These values are applied to every recipient in this campaign. For per-recipient values, set them on each row of the recipient list instead.',
              )
            }}
          </p>
          <FormControl
            v-for="i in bodyParamCount"
            :key="'param-' + i"
            v-model="dialog.template_variables[i - 1]"
            type="text"
            :label="__('Parameter {0}', [i])"
            :placeholder="sampleValues[i - 1] || ''"
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
          :label="__('Send Campaign')"
          :loading="createCampaignResource.loading"
          @click="createCampaign"
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
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { formatDate } from '@/utils'

const campaignsResource = createResource({
  url: 'crm.api.whatsapp.get_bulk_whatsapp_messages',
  cache: 'CRM Bulk WhatsApp Messages',
  auto: false,
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to load bulk campaigns'))
  },
})

const recipientListsResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_recipient_lists',
  cache: 'CRM WhatsApp Recipient Lists',
  auto: false,
})

const templatesResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_templates',
  cache: 'CRM WhatsApp Templates',
  auto: false,
})

const campaigns = computed(() => campaignsResource.data || [])
const recipientLists = computed(() => recipientListsResource.data || [])
const templates = computed(() =>
  (templatesResource.data || []).filter((t) => (t.status || '').toUpperCase() === 'APPROVED'),
)

const recipientListOptions = computed(() => [
  { label: __('Select a recipient list'), value: '' },
  ...recipientLists.value.map((l) => ({
    label: `${l.list_name} (${l.recipient_count})`,
    value: l.name,
  })),
])

const templateOptions = computed(() => [
  { label: __('Select an approved template'), value: '' },
  ...templates.value.map((t) => ({
    label: t.template_name || t.actual_name || t.name,
    value: t.name,
  })),
])

const dialog = ref(emptyDialog())

function emptyDialog() {
  return {
    show: false,
    title: '',
    recipient_list: '',
    template: '',
    template_variables: [],
    error: '',
  }
}

const selectedRecipientList = computed(() =>
  recipientLists.value.find((l) => l.name === dialog.value.recipient_list),
)
const selectedTemplate = computed(() =>
  templates.value.find((t) => t.name === dialog.value.template),
)

function countPlaceholders(text) {
  if (!text) return 0
  const matches = [...text.matchAll(/\{\{\s*(\d+)\s*\}\}/g)].map((m) => parseInt(m[1], 10))
  return matches.length ? Math.max(...matches) : 0
}

const bodyParamCount = computed(() => countPlaceholders(selectedTemplate.value?.template))
const sampleValues = computed(() =>
  selectedTemplate.value?.sample_values
    ? selectedTemplate.value.sample_values.split(',').map((v) => v.trim())
    : [],
)

function openCreateDialog() {
  dialog.value = emptyDialog()
  dialog.value.show = true
  if (recipientLists.value.length === 0) recipientListsResource.reload()
  if (templates.value.length === 0) templatesResource.reload()
}

function progressPercent(c) {
  if (!c.recipient_count) return 0
  return Math.min(100, Math.round(((c.sent_count || 0) / c.recipient_count) * 100))
}

function statusTheme(status) {
  switch (status) {
    case 'Completed':
      return 'green'
    case 'Queued':
    case 'In Progress':
      return 'blue'
    case 'Partially Failed':
      return 'orange'
    case 'Draft':
    default:
      return 'gray'
  }
}

const createCampaignResource = createResource({
  url: 'crm.api.whatsapp.create_bulk_whatsapp_campaign',
  onSuccess() {
    toast.success(__('Bulk WhatsApp campaign queued for sending'))
    dialog.value.show = false
    campaignsResource.reload()
  },
  onError(error) {
    dialog.value.error = error?.messages?.[0] || __('Failed to send bulk campaign')
  },
})

function createCampaign() {
  dialog.value.error = ''
  if (!dialog.value.title?.trim()) {
    dialog.value.error = __('Campaign Title is required')
    return
  }
  if (!dialog.value.recipient_list) {
    dialog.value.error = __('Select a recipient list')
    return
  }
  if (!dialog.value.template) {
    dialog.value.error = __('Select a WhatsApp template')
    return
  }
  if (bodyParamCount.value > 0 && dialog.value.template_variables.filter(Boolean).length < bodyParamCount.value) {
    dialog.value.error = __('Please fill in all template parameters before sending.')
    return
  }

  createCampaignResource.submit({
    title: dialog.value.title,
    template: dialog.value.template,
    recipient_list: dialog.value.recipient_list,
    template_variables: dialog.value.template_variables,
  })
}

const retryResource = createResource({
  url: 'crm.api.whatsapp.retry_failed_bulk_whatsapp_messages',
  onSuccess() {
    toast.success(__('Failed messages requeued for sending'))
    campaignsResource.reload()
  },
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to retry campaign'))
  },
})

const retryingName = ref('')

function retryFailed(c) {
  retryingName.value = c.name
  retryResource.submit({ name: c.name })
}

onMounted(() => {
  campaignsResource.reload()
})
</script>
