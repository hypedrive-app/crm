<template>
  <!-- Fallback card shown when a chat media attachment fails to load — Meta and
       Chatwoot media URLs can expire or 404, and a bare broken-image glyph
       gives the agent no context and no way to reach the file. This keeps the
       message legible and still links to the (possibly re-fetchable) source. -->
  <a
    v-if="href"
    :href="href"
    target="_blank"
    rel="noopener noreferrer"
    class="flex w-56 max-w-full items-center gap-2 rounded-md border border-outline-gray-2 bg-surface-gray-3 px-2.5 py-2 text-ink-gray-5 hover:text-ink-gray-7"
  >
    <span class="lucide-image-off size-4 shrink-0" aria-hidden="true" />
    <span class="truncate text-sm-medium">{{ label }}</span>
    <span class="lucide-external-link ml-auto size-3.5 shrink-0" aria-hidden="true" />
  </a>
  <div
    v-else
    class="flex w-56 max-w-full items-center gap-2 rounded-md border border-outline-gray-2 bg-surface-gray-3 px-2.5 py-2 text-ink-gray-5"
  >
    <span class="lucide-image-off size-4 shrink-0" aria-hidden="true" />
    <span class="truncate text-sm-medium">{{ label }}</span>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  href: { type: String, default: '' },
})
</script>
