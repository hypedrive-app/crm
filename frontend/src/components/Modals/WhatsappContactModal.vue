<template>
  <Dialog v-model:open="show" :title="__('Send Contact')" :size="'lg'">
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="contactName"
          type="text"
          size="md"
          :label="__('Contact Name')"
          :placeholder="__('e.g. Priya Sharma')"
          :required="true"
        />
        <FormControl
          v-model="phone"
          type="text"
          size="md"
          :label="__('Phone Number')"
          placeholder="+919876543210"
          :required="true"
        />

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
import { ref, watch } from 'vue'

const show = defineModel({ type: Boolean })
const emit = defineEmits(['send'])

defineProps({
  sending: { type: Boolean, default: false },
})

const contactName = ref('')
const phone = ref('')
const validationError = ref('')

function resetForm() {
  contactName.value = ''
  phone.value = ''
  validationError.value = ''
}

watch(show, (value) => {
  if (value) resetForm()
})

function confirmSend() {
  if (!contactName.value?.trim()) {
    validationError.value = __('Please enter a contact name.')
    return
  }
  if (!phone.value?.trim()) {
    validationError.value = __('Please enter a phone number.')
    return
  }

  validationError.value = ''
  emit('send', {
    contactName: contactName.value.trim(),
    phone: phone.value.trim(),
  })
}

defineExpose({ resetForm })
</script>
