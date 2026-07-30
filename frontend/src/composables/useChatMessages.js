import { computed, nextTick, ref, watch } from 'vue'
import { sanitizeHTML } from '@/utils'

// Shared chat primitives for the Chatwoot and WhatsApp conversation views.
//
// Both surfaces render the same fundamental thing — a run of messages with a
// direction, a timestamp and a delivery state — but arrived at it from
// different codebases, so grouping existed only on the Chatwoot side and the
// delivery-tick ladder was complete only there too. Everything in this file is
// deliberately transport-agnostic: callers adapt their own message shape
// (Chatwoot's epoch-seconds `created_at` + `direction`, WhatsApp's doctype
// `creation` + `type`) via the accessor options below rather than this module
// knowing about either backend.

// Consecutive messages from the same sender inside this window collapse into
// one visual run (single name label, tight inner gap) — matching WhatsApp Web
// and Stream Chat's published default.
export const GROUP_WINDOW_SECONDS = 60

/**
 * Groups a flat message list into visual runs.
 *
 * A new group starts when the direction changes, the sender changes, the gap
 * exceeds GROUP_WINDOW_SECONDS, or the message is a system/activity notice
 * (which never merges with anything, in either direction).
 *
 * @param messages    Ref/getter for the message array.
 * @param options.direction  (message) => string  e.g. 'incoming' | 'outgoing' | 'activity'
 * @param options.timestamp  (message) => number  seconds since epoch
 * @param options.senderId   (message) => string|number|null
 * @param options.id         (message) => string|number  stable per-message key
 * @param options.standalone (message) => boolean  never merge this message
 */
export function useMessageGrouping(messages, options = {}) {
  const {
    direction = (m) => m.direction || 'unknown',
    timestamp = (m) => m.created_at || 0,
    senderId = (m) => m.sender?.id ?? m.sender?.name ?? null,
    id = (m) => m.id,
    standalone = () => false,
  } = options

  return computed(() => {
    const groups = []
    for (const message of messages.value || []) {
      const dir = direction(message)
      const at = timestamp(message)
      const sender = senderId(message)
      const isStandalone = dir === 'activity' || standalone(message)
      const last = groups[groups.length - 1]

      const sameBucket =
        last &&
        !isStandalone &&
        !last.standalone &&
        last.direction === dir &&
        last.senderId === sender &&
        at - last.lastTimestamp <= GROUP_WINDOW_SECONDS

      if (sameBucket) {
        last.messages.push(message)
        last.lastTimestamp = at
      } else {
        groups.push({
          key: `${dir}-${id(message)}`,
          direction: dir,
          senderId: sender,
          standalone: isStandalone,
          lastTimestamp: at,
          messages: [message],
        })
      }
    }
    return groups
  })
}

/**
 * Client-side, conversation-scoped message search shared by both views.
 *
 * Neither backend exposes a conversation-scoped search endpoint (Chatwoot has
 * none at all; the WhatsApp doctype would need a new whitelisted method), so
 * this only ever narrows the already-fetched thread — it never triggers a
 * request. Groups are filtered down to their matching messages rather than
 * dropped whole, so a hit inside a multi-message run still renders with its
 * sender context intact. Activity/system groups are dropped once a query is
 * active: this is a message search, not a system-log search.
 *
 * @param groups   Computed group list (from useMessageGrouping).
 * @param options.text (message) => string  searchable text for a message.
 * @param options.resetOn  Ref watched to clear the query (e.g. active conversation id).
 */
export function useMessageSearch(groups, options = {}) {
  const { text = (m) => m.content || '', resetOn = null } = options

  const showSearch = ref(false)
  const searchQuery = ref('')
  const searchInputRef = ref(null)

  function focusInput() {
    nextTick(() => searchInputRef.value?.el?.focus())
  }

  function toggleSearch() {
    showSearch.value = !showSearch.value
    if (showSearch.value) {
      focusInput()
    } else {
      searchQuery.value = ''
    }
  }

  function clearSearch() {
    searchQuery.value = ''
    focusInput()
  }

  // Escape clears the query first, then closes the bar on a second press.
  function onSearchEscape() {
    if (searchQuery.value) {
      searchQuery.value = ''
    } else {
      showSearch.value = false
    }
  }

  const filteredGroups = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()
    if (!query) return groups.value

    const result = []
    for (const group of groups.value) {
      if (group.direction === 'activity') continue
      const matches = group.messages.filter((m) =>
        (text(m) || '').toLowerCase().includes(query),
      )
      if (matches.length) result.push({ ...group, messages: matches })
    }
    return result
  })

  const visibleGroups = computed(() =>
    searchQuery.value.trim() ? filteredGroups.value : groups.value,
  )

  // Switching conversations must never leave a stale query or open bar behind.
  if (resetOn) {
    watch(resetOn, () => {
      showSearch.value = false
      searchQuery.value = ''
    })
  }

  return {
    showSearch,
    searchQuery,
    searchInputRef,
    filteredGroups,
    visibleGroups,
    toggleSearch,
    clearSearch,
    onSearchEscape,
  }
}

const HTML_ESCAPES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function escapeHTML(text) {
  return String(text).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char])
}

/**
 * Renders WhatsApp's wire markup (*bold*, _italic_, ~strike~, `code`) to HTML.
 *
 * Escapes the source text BEFORE applying any markup, so message content can
 * never contribute raw markup to the output — the previous implementation
 * built HTML directly out of unescaped user text and relied solely on
 * DOMPurify to clean up afterwards, which is a strictly weaker position (it
 * only holds as long as every regex and DOMPurify's default config stay
 * exactly right). Output still passes through sanitizeHTML as defence in
 * depth. Returns '' for null/undefined/non-string input; several callers pass
 * message bodies that are genuinely absent (media with no caption).
 */
export function formatWhatsAppMarkup(message) {
  if (message == null) return ''
  let text = escapeHTML(message)

  // Order matters throughout.
  // 1. Code fences first, so markup inside them is left alone.
  text = text.replace(/```([\s\S]*?)```/g, '<code>$1</code>')
  text = text.replace(/`([^`\n]+?)`/g, '<code>$1</code>')

  // 2. List items, while line structure is still intact. Anchored to
  //    line-start (`^`, multiline) so a mid-sentence "2 * 3" or a hyphenated
  //    word is never mistaken for a bullet — the previous implementation
  //    matched `* ` anywhere in the string and mangled exactly those cases.
  //    Consecutive items are wrapped in a single <ul> so the browser renders a
  //    real list rather than orphaned <li> elements.
  text = text.replace(/^\s*[*-] +(.*)$/gm, '<li>$1</li>')
  text = text.replace(/^\s*\d+\. +(.*)$/gm, '<li>$1</li>')
  text = text.replace(/(?:<li>.*?<\/li>\n?)+/gs, (run) => `<ul>${run.trim()}</ul>`)

  // 3. Blockquotes ('>' is already escaped to '&gt;' at this point).
  text = text.replace(/^&gt; (.*)$/gm, '<blockquote>$1</blockquote>')

  // 4. Inline emphasis. Bounded to a single line and required to sit on a word
  //    boundary, so `snake_case_name` and `a * b` stay literal.
  text = text.replace(/(^|\s)\*([^*\n]+?)\*(?=\s|$)/g, '$1<b>$2</b>')
  text = text.replace(/(^|\s)_([^_\n]+?)_(?=\s|$)/g, '$1<i>$2</i>')
  text = text.replace(/(^|\s)~([^~\n]+?)~(?=\s|$)/g, '$1<s>$2</s>')

  // 5. Remaining newlines become breaks — but not the ones adjacent to
  //    block-level tags, which already break the line themselves. Dropping
  //    those first prevents a stray <br> landing between two <li> elements
  //    (visible as a blank row inside every list) or after a </ul>.
  text = text.replace(/\n(?=<li>|<\/ul>|<blockquote>)/g, '')
  text = text.replace(/(<\/li>|<\/ul>|<\/blockquote>)\n/g, '$1')
  text = text.replace(/\n/g, '<br>')

  return sanitizeHTML(text)
}

/**
 * Chatwoot delivers plain text with newlines; no inline markup vocabulary.
 * Escaped first for the same reason as above.
 */
export function formatPlainMessage(message) {
  if (message == null) return ''
  return sanitizeHTML(escapeHTML(message).replace(/\n/g, '<br>'))
}
