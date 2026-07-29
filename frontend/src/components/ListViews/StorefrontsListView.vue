<template>
  <ListView
    :class="$attrs.class"
    :columns="visibleColumns"
    :rows="rows"
    :options="{
      selectable: options.selectable,
      showTooltip: options.showTooltip,
      resizeColumn: options.resizeColumn,
    }"
    row-key="name"
    @update:selections="(selections) => emit('selectionsChanged', selections)"
  >
    <ListHeader
      class="mx-3 sm:mx-5"
      @columnWidthUpdated="emit('columnWidthUpdated')"
    >
      <ListHeaderItem
        v-for="column in visibleColumns"
        :key="column.key"
        :item="column"
        @columnWidthUpdated="(e) => onColumnWidthUpdated(e, column)"
      />
    </ListHeader>
    <ListRows
      v-slot="{ idx, column, item }"
      class="mx-3 sm:mx-5"
      :rows="rows"
      doctype="CRM Storefront"
    >
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden">
        <template #prefix>
          <div v-if="column.key === 'organization'">
            <Avatar
              v-if="item.label"
              class="flex items-center"
              :image="item.logo"
              :label="item.label"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'store_url' && item.label">
            <FeatherIcon name="external-link" class="h-3.5 w-3.5 text-ink-gray-5" />
          </div>
        </template>
        <template #default="{ label }">
          <div
            v-if="column.key === 'platform'"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            <Badge v-if="label" :label="label" variant="subtle" theme="gray">
              <template v-if="getPlatformLogoUrl(label)" #prefix>
                <img
                  :src="getPlatformLogoUrl(label)"
                  class="size-3 rounded-sm"
                  alt=""
                />
              </template>
            </Badge>
          </div>
          <div
            v-else-if="column.key === 'store_url' && label"
            class="truncate text-base text-ink-blue-3 hover:underline"
            @click.stop="openWebsite(item.url)"
          >
            {{ label }}
          </div>
          <div
            v-else-if="['modified', 'creation'].includes(column.key)"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            <Tooltip :text="item.label">
              <div>{{ item.timeAgo }}</div>
            </Tooltip>
          </div>
          <div
            v-else-if="label"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ getLabel(label, column) }}
          </div>
        </template>
      </ListRowItem>
    </ListRows>
    <ListSelectBanner>
      <template #actions="{ selections, unselectAll }">
        <Dropdown
          :options="listBulkActionsRef.bulkActions(selections, unselectAll)"
        >
          <Button icon="lucide-more-horizontal" variant="ghost" />
        </Dropdown>
      </template>
    </ListSelectBanner>
  </ListView>
  <ListFooter
    v-if="pageLengthCount"
    v-model="pageLengthCount"
    class="border-t px-3 py-2 sm:px-5"
    :options="{
      rowCount: options.rowCount,
      totalCount: options.totalCount,
    }"
    @loadMore="emit('loadMore')"
  />
  <ListBulkActions
    ref="listBulkActionsRef"
    v-model="list"
    doctype="CRM Storefront"
    :options="{
      hideAssign: true,
    }"
  />
</template>
<script setup>
import ListBulkActions from '@/components/ListBulkActions.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import { isTranslatable, formatDuration, openWebsite } from '@/utils'
import { isMobileView } from '@/composables/settings'
import { getPlatformLogoUrl } from '@/utils/platformLogo'
import {
  Avatar,
  Badge,
  FeatherIcon,
  ListView,
  ListHeader,
  ListHeaderItem,
  ListSelectBanner,
  ListRowItem,
  ListFooter,
  Tooltip,
  Dropdown,
} from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
  options: {
    type: Object,
    default: () => ({
      selectable: true,
      showTooltip: true,
      resizeColumn: false,
      totalCount: 0,
      rowCount: 0,
    }),
  },
})

const emit = defineEmits([
  'loadMore',
  'updatePageCount',
  'columnWidthUpdated',
  'applyFilter',
  'selectionsChanged',
])

const pageLengthCount = defineModel({ type: Number })
const list = defineModel('list', { type: Object })

// See LeadsListView.vue: trims the fixed-grid columns to title + one field
// on mobile so the row doesn't require horizontal scrolling to read.
const visibleColumns = computed(() =>
  isMobileView.value ? props.columns.slice(0, 2) : props.columns,
)

function onColumnWidthUpdated({ width, save }, column) {
  column.width = width
  if (save) emit('columnWidthUpdated', column)
}

function getLabel(label, column) {
  if (column.type === 'Duration') return formatDuration(label)
  if (column.options && isTranslatable(column.options)) return __(label)
  return label
}

watch(pageLengthCount, (val, old_value) => {
  if (val === old_value) return
  emit('updatePageCount', val)
})

const listBulkActionsRef = ref(null)

defineExpose({
  customListActions: null,
})
</script>
