<template>
  <Dialog v-model:open="show" :title="__('Canned Responses')" :size="'4xl'">
    <template #default>
      <div class="w-full flex items-center gap-2">
        <TextInput
          ref="searchInput"
          v-model="search"
          class="w-full"
          type="text"
          :placeholder="__('Search by shortcut or content...')"
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
        v-if="cannedResponses.loading"
        class="mt-2 flex h-56 items-center justify-center"
      >
        <LoadingIndicator class="size-6" />
      </div>
      <div
        v-else-if="filteredResponses.length"
        class="mt-2 grid max-h-[560px] grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-2"
      >
<!-- min-h (not fixed h-32) so short responses shrink; line-clamp still caps long ones. -->
        <div
          v-for="response in filteredResponses"
          :key="response.id"
          class="flex min-h-32 cursor-pointer flex-col gap-1 rounded-lg border border-outline-gray-2 p-3 hover:bg-surface-gray-2"
          @click="emit('send', response.content)"
        >
          <!-- border-outline-gray-2 so the divider is theme-aware (bare `border-b` reads wrong in dark mode). -->
          <div
            class="border-b border-outline-gray-2 pb-1.5 text-base-semibold truncate"
            :title="response.short_code"
          >
            {{ response.short_code }}
          </div>
          <div class="flex-1 overflow-hidden text-p-sm text-ink-gray-6 line-clamp-4">
            {{ response.content }}
          </div>
        </div>
      </div>
      <div v-else class="mt-2">
        <div class="flex h-56 flex-col items-center justify-center">
          <div class="text-lg text-ink-gray-4">
            {{ __('No Canned Responses Found') }}
          </div>
          <div class="mt-1 text-p-sm text-ink-gray-5">
            {{
              __(
                'Add canned responses in Chatwoot under Settings > Canned Responses.',
              )
            }}
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { LoadingIndicator, createResource } from 'frappe-ui'
import { ref, computed, nextTick, watch } from 'vue'

const show = defineModel({ type: Boolean })
const searchInput = ref('')

const emit = defineEmits(['send'])

const search = ref('')

const cannedResponses = createResource({
  url: 'crm.api.chatwoot.get_chatwoot_canned_responses',
  cache: 'chatwoot_canned_responses',
  auto: true,
})

const filteredResponses = computed(() => {
  const query = search.value.toLowerCase()
  return (
    cannedResponses.data?.filter(
      (response) =>
        response.short_code.toLowerCase().includes(query) ||
        response.content.toLowerCase().includes(query),
    ) ?? []
  )
})

watch(show, (value) => value && nextTick(() => searchInput.value?.el?.focus()))
</script>
