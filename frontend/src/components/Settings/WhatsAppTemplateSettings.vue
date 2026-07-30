<template>
  <SettingsLayoutBase
    :title="__('WhatsApp Templates')"
    :description="
      __(
        'Templates synced from your Meta WhatsApp Business Account. Create or edit templates in Meta / Frappe Desk, then sync to pull their latest approval status here.',
      )
    "
  >
    <template #header-actions>
      <Button
        variant="solid"
        icon-left="lucide-refresh-cw"
        :loading="syncResource.loading"
        @click="syncTemplates"
      >
        {{ __('Sync from Meta') }}
      </Button>
    </template>
    <template #content>
      <div
        v-if="templatesResource.loading && !templatesResource.data"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
      <div
        v-else-if="!templates.length"
        class="relative flex h-full w-full justify-center"
      >
        <div
          class="absolute left-1/2 flex w-72 -translate-x-1/2 flex-col items-center gap-3"
          :style="{ top: '25%' }"
        >
          <WhatsAppIcon class="size-7.5 text-ink-gray-5" />
          <div class="flex flex-col items-center gap-1.5 text-center">
            <span class="text-lg-medium text-ink-gray-8">
              {{ __('No WhatsApp Templates Yet') }}
            </span>
            <span class="text-center text-p-base text-ink-gray-6">
              {{
                __(
                  'Sync from Meta to pull in templates created for your WhatsApp Business Account.',
                )
              }}
            </span>
            <Button
              variant="solid"
              :loading="syncResource.loading"
              @click="syncTemplates"
            >
              {{ __('Sync from Meta') }}
            </Button>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-col gap-3">
        <TextInput
          v-model="search"
          type="text"
          :placeholder="__('Search templates')"
          class="w-full sm:w-72"
        >
          <template #prefix>
            <span
              class="lucide-search h-4 w-4 text-ink-gray-4"
              aria-hidden="true"
            />
          </template>
        </TextInput>
        <div class="overflow-x-auto rounded-lg border border-outline-elevation-2">
          <table class="w-full min-w-[720px] text-left text-p-sm">
            <thead>
              <tr class="border-b border-outline-elevation-2 bg-surface-gray-1">
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Template') }}
                </th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Category') }}
                </th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Language') }}
                </th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Status') }}
                </th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Body') }}
                </th>
                <th class="px-3 py-2 font-medium text-ink-gray-6">
                  {{ __('Last Synced') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="tpl in filteredTemplates"
                :key="tpl.name"
                class="border-b border-outline-elevation-2 last:border-b-0 align-top hover:bg-surface-gray-1"
              >
                <td class="px-3 py-2">
                  <div class="text-p-sm-medium text-ink-gray-8">
                    {{ tpl.template_name || tpl.actual_name || tpl.name }}
                  </div>
                  <div
                    v-if="tpl.actual_name"
                    class="text-xs text-ink-gray-5"
                  >
                    {{ tpl.actual_name }}
                  </div>
                </td>
                <td class="px-3 py-2">
                  <Badge
                    v-if="tpl.category"
                    :label="tpl.category"
                    theme="gray"
                    variant="subtle"
                  />
                  <span v-else class="text-ink-gray-4">-</span>
                </td>
                <td class="px-3 py-2 whitespace-nowrap text-ink-gray-6">
                  {{ tpl.language_code || tpl.language || '-' }}
                </td>
                <td class="px-3 py-2">
                  <Badge
                    :label="tpl.status || __('Unknown')"
                    :theme="statusTheme(tpl.status)"
                    variant="subtle"
                  />
                </td>
                <td class="px-3 py-2 min-w-[260px] max-w-[420px]">
                  <div
                    v-if="tpl.header"
                    class="mb-1 text-xs-medium text-ink-gray-7"
                  >
                    {{ tpl.header }}
                  </div>
                  <div class="whitespace-pre-line text-ink-gray-6">
                    {{ tpl.template || __('No body text') }}
                  </div>
                  <div
                    v-if="tpl.footer"
                    class="mt-1 text-xs text-ink-gray-5"
                  >
                    {{ tpl.footer }}
                  </div>
                </td>
                <td class="px-3 py-2 whitespace-nowrap text-ink-gray-5">
                  {{ formatDate(tpl.modified) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredTemplates.length" class="py-6 text-center text-p-sm text-ink-gray-5">
          {{ __('No templates match your search.') }}
        </div>
      </div>
    </template>
  </SettingsLayoutBase>
</template>
<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import { Badge, Button, LoadingIndicator, TextInput, createResource, toast } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { formatDate } from '@/utils'

const search = ref('')

const templatesResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_templates',
  cache: 'CRM WhatsApp Templates',
  auto: false,
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to load WhatsApp templates'))
  },
})

const syncResource = createResource({
  url: 'crm.api.whatsapp.sync_whatsapp_templates',
  onSuccess() {
    toast.success(__('WhatsApp templates synced from Meta'))
    // Only refresh the list once the sync has actually succeeded, so a
    // failed sync never wipes out the previously-loaded (still valid) list.
    templatesResource.reload()
  },
  onError(error) {
    toast.error(error?.messages?.[0] || __('Failed to sync WhatsApp templates'))
  },
})

const templates = computed(() => templatesResource.data || [])

const filteredTemplates = computed(() => {
  if (!search.value) return templates.value
  const query = search.value.toLowerCase()
  return templates.value.filter((tpl) => {
    return (
      (tpl.template_name || '').toLowerCase().includes(query) ||
      (tpl.actual_name || '').toLowerCase().includes(query) ||
      (tpl.template || '').toLowerCase().includes(query) ||
      (tpl.category || '').toLowerCase().includes(query)
    )
  })
})

function statusTheme(status) {
  switch ((status || '').toUpperCase()) {
    case 'APPROVED':
      return 'green'
    case 'PENDING':
    case 'IN_APPEAL':
    case 'PENDING_DELETION':
      return 'orange'
    case 'REJECTED':
    case 'DISABLED':
    case 'PAUSED':
      return 'red'
    default:
      return 'gray'
  }
}

function syncTemplates() {
  syncResource.submit()
}

onMounted(() => {
  templatesResource.reload()
})
</script>
