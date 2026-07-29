import { useWindowSize } from '@vueuse/core'
import { computed, ref } from 'vue'

export const mobileSidebarOpened = ref(false)

// window.innerWidth read once at module-init time never updates on resize
// or rotate — useWindowSize's width is a live ref, so this now actually
// reacts instead of requiring a full page reload to notice a viewport
// change (e.g. rotating a tablet, or a devtools viewport resize).
const { width } = useWindowSize()
export const isMobileView = computed(() => width.value < 768)

export const showSettings = ref(false)

export const disableSettingModalOutsideClick = ref(false)

export const activeSettingsPage = ref('')
