<!--
  EnrichMore.vue - button-controlled trigger for the three API-type Server
  Scripts (apollo_enrichment, hunter_enrichment, gst_enrichment) on CRM
  Organization. Sibling to EnrichFromWebsite.vue (the native domain/logo
  "Enrich" button) - same idioms (frappe-ui Button/call/toast), but these
  three run SYNCHRONOUSLY inline (Server Scripts, no background job/
  websocket), so this component polls nothing and just awaits call().
-->
<template>
  <Dropdown :options="options" placement="right">
    <template #default="{ open }">
      <Button :label="running ? '' : __('Enrich More')" :loading="running" :disabled="running">
        <template v-if="!running" #suffix>
          <FeatherIcon :name="open ? 'chevron-up' : 'chevron-down'" class="h-4 w-4" />
        </template>
      </Button>
    </template>
  </Dropdown>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, Dropdown, FeatherIcon, call, toast } from 'frappe-ui'

const props = defineProps({
  docname: { type: String, required: true },
  website: { type: String, default: '' },
  gstin: { type: String, default: '' },
})

const emit = defineEmits(['done'])

const running = ref(false)

async function run(apiMethod, label, requiresField, requiresLabel) {
  if (requiresField !== undefined && !(requiresField || '').trim()) {
    toast.warning(__('Set {0} on this record before enriching.', [requiresLabel]))
    return
  }
  running.value = true
  try {
    const result = await call(apiMethod, { reference_name: props.docname })
    if (result?.status === 'success') {
      const filled = result.filled_fields || []
      toast.success(
        filled.length
          ? __('{0}: filled {1}', [label, filled.join(', ')])
          : __('{0}: done', [label])
      )
      emit('done')
    } else if (result?.status === 'skipped' || result?.status === 'no_data' || result?.status === 'not_valid') {
      toast.warning(result.message || __('{0}: nothing to update.', [label]))
    } else {
      toast.warning(result?.error || __('{0}: no result.', [label]))
    }
  } catch (error) {
    // Server Script errors (incl. the surfaced upstream Apollo/kyc-service
    // messages, e.g. a real 422 quota error or a GSTIN checksum failure)
    // arrive as error.messages from frappe-ui's call() wrapper.
    toast.error(error.messages?.[0] || error.message || __('{0} failed.', [label]))
  } finally {
    running.value = false
  }
}

const options = computed(() => [
  {
    label: __('Apollo (industry)'),
    onClick: () => run('apollo_enrichment', __('Apollo'), props.website, __('a Website')),
  },
  {
    label: __('Hunter (decision-maker contact)'),
    onClick: () => run('hunter_enrichment', __('Hunter'), props.website, __('a Website')),
  },
  {
    label: __('GST (registration details)'),
    onClick: () => run('gst_enrichment', __('GST'), props.gstin, __('a GSTIN')),
  },
])
</script>
