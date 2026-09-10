import * as React from "react"

const MOBILE_BREAKPOINT = 768

const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

/**
 * Track whether the viewport is mobile-sized.
 *
 * Implemented with useSyncExternalStore rather than an effect that calls
 * setState: matchMedia is an external store, and subscribing to it directly
 * avoids the extra render pass the effect version caused on every mount.
 * It also gives a defined value on the first client render instead of
 * flashing the desktop layout for a frame.
 */
function subscribe(onStoreChange: () => void): () => void {
  const query = window.matchMedia(QUERY)
  query.addEventListener("change", onStoreChange)
  return () => query.removeEventListener("change", onStoreChange)
}

function getSnapshot(): boolean {
  return window.matchMedia(QUERY).matches
}

/** On the server there is no viewport; assume desktop, which is the
 * primary target for this application. */
function getServerSnapshot(): boolean {
  return false
}

export function useIsMobile(): boolean {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
