import { createResource } from 'frappe-ui'
import { ref } from 'vue'

export const chatwootEnabled = ref(false)
export const isChatwootInstalled = ref(false)

createResource({
  url: 'crm.api.chatwoot.is_chatwoot_enabled',
  cache: 'Is Chatwoot Enabled',
  auto: true,
  onSuccess: (data) => {
    chatwootEnabled.value = Boolean(data)
  },
})

createResource({
  url: 'crm.api.chatwoot.is_chatwoot_installed',
  cache: 'Is Chatwoot Installed',
  auto: true,
  onSuccess: (data) => {
    isChatwootInstalled.value = Boolean(data)
  },
})
