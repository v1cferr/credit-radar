import * as React from "react";

import {
  DARK_QUERY,
  readThemeSetting,
  THEME_CHANGE_EVENT,
  type ThemeSetting,
} from "@/components/app-shell/theme";

/**
 * Track the reader's theme setting.
 *
 * `localStorage` is an external store, so it is read through
 * `useSyncExternalStore` rather than copied into state by an effect. That
 * keeps the value in one place and gives a defined answer on the first
 * client render, instead of rendering a guess and correcting it.
 *
 * Three sources can change it: this tab's own control, another tab, and
 * the operating system while the setting is "system".
 */
function subscribe(onStoreChange: () => void): () => void {
  const query = window.matchMedia(DARK_QUERY);
  query.addEventListener("change", onStoreChange);
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(THEME_CHANGE_EVENT, onStoreChange);

  return () => {
    query.removeEventListener("change", onStoreChange);
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(THEME_CHANGE_EVENT, onStoreChange);
  };
}

function getSnapshot(): ThemeSetting {
  return readThemeSetting();
}

/**
 * The server cannot know a value kept in the reader's browser, so it
 * renders the default. React re-reads the real one immediately after
 * hydration; the colours themselves were already right, applied by the
 * blocking script in the layout before the first paint.
 */
function getServerSnapshot(): ThemeSetting {
  return "system";
}

export function useThemeSetting(): ThemeSetting {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
