import { createResource } from 'frappe-ui'
import { ref } from 'vue'

export const whatsappEnabled = ref(false)
export const isWhatsappInstalled = ref(false)

// WHY these cache keys are namespaced ("crm:whatsapp:..."):
// frappe-ui keys createResource by `cache` in a module-global map. If any OTHER
// createResource is registered with the same bare key first, this call returns
// that pre-existing resource and SILENTLY DROPS the options passed here —
// including these onSuccess/onData callbacks — so the enabled ref would never
// resolve and the tab would gate on a stale `false` forever. A distinctive,
// app-scoped key avoids colliding with any other resource.
//
// WHY onData (not onSuccess): onSuccess fires only after a live network fetch.
// onData ALSO fires on a cache hit (the local/offline path in frappe-ui reads
// the stored value and calls onData, never onSuccess). Using onData means the
// ref resolves reliably whether the value comes fresh or from cache.
//
// WHY the synchronous `.data` read below: createResource returns immediately;
// if this resource instance was created earlier (e.g. by another importer) it
// may already hold data, in which case neither callback fires again for us.
// Seeding from the current `.data` closes that race so the ref is never left
// stale at its initial `false`.

function syncEnabled(target, data) {
  target.value = Boolean(data)
}

const whatsappEnabledResource = createResource({
  url: 'crm.api.whatsapp.is_whatsapp_enabled',
  cache: 'crm:whatsapp:is_enabled',
  auto: true,
  onData: (data) => syncEnabled(whatsappEnabled, data),
  onError: () => {
    // Fail closed: a failed check must NOT leave a truthy value that gates the
    // tab open. Keep the flag false so a broken/misconfigured backend hides the
    // feature rather than showing a tab that can't work.
    whatsappEnabled.value = false
  },
})
if (whatsappEnabledResource.data != null) {
  syncEnabled(whatsappEnabled, whatsappEnabledResource.data)
}

const whatsappInstalledResource = createResource({
  url: 'crm.api.whatsapp.is_whatsapp_installed',
  cache: 'crm:whatsapp:is_installed',
  auto: true,
  onData: (data) => syncEnabled(isWhatsappInstalled, data),
  onError: () => {
    isWhatsappInstalled.value = false
  },
})
if (whatsappInstalledResource.data != null) {
  syncEnabled(isWhatsappInstalled, whatsappInstalledResource.data)
}
