<template>
  <!-- Match the CRMLogo fallback's rounded corners; without this a custom
       brand logo renders with hard square corners against an otherwise
       all-rounded UI (most visible in the mobile sidebar drawer). -->
  <div v-if="brand?.logo" class="overflow-hidden rounded">
    <img :src="brand.logo" class="h-full w-full object-cover" />
  </div>
  <CRMLogo v-else class="size-8 shrink-0 rounded" />
</template>

<script setup>
import CRMLogo from '@/components/Icons/CRMLogo.vue'

const brand = defineModel({ type: Object, default: () => ({}) })
</script>
