<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Storefronts" />
    </template>
    <template #right-header>
      <CustomActions
        v-if="storefrontsListView?.customListActions"
        :actions="storefrontsListView.customListActions"
      />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="storefronts"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Storefront"
  />
  <StorefrontsListView
    v-if="storefronts.data && rows.length"
    ref="storefrontsListView"
    v-model="storefronts.data.page_length_count"
    v-model:list="storefronts"
    :rows="rows"
    :columns="columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: storefronts.data.row_count,
      totalCount: storefronts.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @applyFilter="(data) => viewControls.applyFilter(data)"
    @selectionsChanged="
      (selections) => viewControls.updateSelections(selections)
    "
  />
  <EmptyState
    v-else-if="storefronts.data && !rows.length"
    name="Storefronts"
    :icon="StorefrontsIcon"
  />
</template>
<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import CustomActions from '@/components/CustomActions.vue'
import StorefrontsIcon from '@/components/Icons/StorefrontsIcon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import StorefrontsListView from '@/components/ListViews/StorefrontsListView.vue'
import ViewControls from '@/components/ViewControls.vue'
import { formatDate, website } from '@/utils'
import { timestampCell } from '@/composables/useTimelinePreferences'
import { ref, computed } from 'vue'
import EmptyState from '../components/ListViews/EmptyState.vue'

const storefrontsListView = ref(null)

// storefronts data is loaded in the ViewControls component
const storefronts = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (
    !storefronts.value?.data?.data ||
    !['list', 'group_by'].includes(storefronts.value.data.view_type)
  )
    return []
  return storefronts.value?.data.data.map((storefront) => {
    let _rows = {}
    storefronts.value?.data.rows.forEach((row) => {
      _rows[row] = storefront[row]

      let fieldType = storefronts.value?.data.columns?.find(
        (col) => (col.key || col.value) == row,
      )?.type

      if (
        fieldType &&
        ['Date', 'Datetime'].includes(fieldType) &&
        !['modified', 'creation'].includes(row)
      ) {
        _rows[row] = formatDate(
          storefront[row],
          '',
          true,
          fieldType == 'Datetime',
        )
      }

      if (row === 'organization') {
        _rows[row] = {
          label: storefront.organization,
          logo: storefront.organization_logo,
        }
      } else if (row === 'store_url') {
        _rows[row] = {
          label: website(storefront.store_url),
          url: storefront.store_url,
        }
      } else if (['modified', 'creation'].includes(row)) {
        _rows[row] = timestampCell(storefront[row])
      }
    })
    return _rows
  })
})

const columns = computed(() => {
  let _columns = storefronts.value?.data?.columns || []

  // Set align right for last column
  if (_columns.length) {
    _columns = _columns.map((col, index) => {
      if (index === _columns.length - 1) {
        return { ...col, align: 'right' }
      }
      return col
    })
  }

  return _columns
})
</script>
