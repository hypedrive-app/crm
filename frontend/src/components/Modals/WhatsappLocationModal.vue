<template>
  <Dialog v-model:open="show" :title="__('Send Location')" :size="'lg'">
    <template #default>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
          <Button
            :label="
              locating
                ? __('Getting current location...')
                : __('Use My Current Location')
            "
            icon-left="lucide-map-pin"
            :loading="locating"
            @click="useCurrentLocation"
          />
          <div v-if="geoError" class="text-sm text-ink-red-4">
            {{ geoError }}
          </div>
          <div class="text-sm text-ink-gray-5">
            {{ __('Or enter coordinates manually below.') }}
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <FormControl
            v-model="latitude"
            type="text"
            size="md"
            :label="__('Latitude')"
            placeholder="12.9715987"
          />
          <FormControl
            v-model="longitude"
            type="text"
            size="md"
            :label="__('Longitude')"
            placeholder="77.5945627"
          />
        </div>

        <FormControl
          v-model="name"
          type="text"
          size="md"
          :label="__('Location Name (optional)')"
          :placeholder="__('e.g. Office HQ')"
        />
        <FormControl
          v-model="address"
          type="textarea"
          size="md"
          :label="__('Address (optional)')"
          :rows="2"
        />

        <div
          v-if="hasCoordinates"
          class="rounded-md border border-outline-gray-2 p-2.5"
        >
          <div class="flex items-center gap-1.5 text-sm-medium text-ink-gray-8">
            <span class="lucide-map-pin size-3.5 shrink-0" aria-hidden="true" />
            {{ name || __('Pinned Location') }}
          </div>
          <div class="mt-0.5 text-xs text-ink-gray-5">
            {{ latitude }}, {{ longitude }}
          </div>
        </div>

        <ErrorMessage :message="validationError" />

        <div class="flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="show = false" />
          <Button
            :label="__('Send')"
            variant="solid"
            :loading="sending"
            @click="confirmSend"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Dialog, FormControl, ErrorMessage } from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const show = defineModel({ type: Boolean })
const emit = defineEmits(['send'])

defineProps({
  sending: { type: Boolean, default: false },
})

const latitude = ref('')
const longitude = ref('')
const name = ref('')
const address = ref('')
const validationError = ref('')
const geoError = ref('')
const locating = ref(false)

const hasCoordinates = computed(() => {
  const lat = Number(latitude.value)
  const long = Number(longitude.value)
  return latitude.value !== '' && longitude.value !== '' && !isNaN(lat) && !isNaN(long)
})

function useCurrentLocation() {
  geoError.value = ''
  if (!navigator.geolocation) {
    geoError.value = __('Your browser does not support geolocation.')
    return
  }
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      latitude.value = String(position.coords.latitude)
      longitude.value = String(position.coords.longitude)
      locating.value = false
    },
    (error) => {
      locating.value = false
      geoError.value =
        error.code === error.PERMISSION_DENIED
          ? __('Location permission was denied. Please enter coordinates manually.')
          : __('Could not get your current location. Please enter coordinates manually.')
    },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

function resetForm() {
  latitude.value = ''
  longitude.value = ''
  name.value = ''
  address.value = ''
  validationError.value = ''
  geoError.value = ''
  locating.value = false
}

watch(show, (value) => {
  if (value) resetForm()
})

function confirmSend() {
  const lat = Number(latitude.value)
  const long = Number(longitude.value)

  if (latitude.value === '' || longitude.value === '' || isNaN(lat) || isNaN(long)) {
    validationError.value = __('Please provide valid latitude and longitude.')
    return
  }
  if (lat < -90 || lat > 90 || long < -180 || long > 180) {
    validationError.value = __(
      'Latitude must be between -90 and 90, and longitude between -180 and 180.',
    )
    return
  }

  validationError.value = ''
  emit('send', {
    latitude: lat,
    longitude: long,
    name: name.value?.trim() || '',
    address: address.value?.trim() || '',
  })
}

defineExpose({ resetForm })
</script>
