import { refDebounced, useWindowSize } from '@vueuse/core'
import { computed, ref } from 'vue'

export const mobileSidebarOpened = ref(false)

// window.innerWidth read once at module-init time never updates on resize
// or rotate — useWindowSize's width is a live ref, so this now actually
// reacts instead of requiring a full page reload to notice a viewport
// change (e.g. rotating a tablet, or a devtools viewport resize).
//
// Several consumers (ViewControls, CustomActions, Filter) v-if-swap between
// structurally different toolbar/button layouts based on isMobileView. On
// mobile browsers the reported width can jitter across the 768px line
// transiently — e.g. the address bar collapsing/expanding on scroll, or the
// on-screen keyboard opening on a device near the breakpoint — which made
// those toolbars visibly reflow/reposition mid-session. Debouncing the
// width read absorbs that jitter while still tracking real rotations/resizes.
const { width } = useWindowSize()
const debouncedWidth = refDebounced(width, 200)
export const isMobileView = computed(() => debouncedWidth.value < 768)

export const showSettings = ref(false)

export const disableSettingModalOutsideClick = ref(false)

export const activeSettingsPage = ref('')
