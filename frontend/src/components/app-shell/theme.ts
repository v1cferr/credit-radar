/**
 * Theme selection.
 *
 * Three settings, not two. "System" is the default and it is a real choice
 * rather than an initial value: a phone that turns dark at sunset should
 * take this dashboard with it, and a toggle that only remembers light or
 * dark quietly opts the reader out of that forever.
 *
 * The stylesheet keys off a `dark` class on the document element, so the
 * only job here is deciding when that class is present.
 */

export type ThemeSetting = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "credit-radar-theme";

export const DARK_QUERY = "(prefers-color-scheme: dark)";

/**
 * Fired when this tab changes the setting.
 *
 * The `storage` event only reaches *other* tabs, so without this the
 * control that was just pressed would not hear about its own change.
 */
export const THEME_CHANGE_EVENT = "credit-radar:theme-change";

/**
 * Script that resolves the theme before the page paints.
 *
 * Inline and blocking on purpose. Applied from a React effect instead, the
 * first frame would be light and then flip -- which on a dashboard opened
 * at night is a white flash in a dark room. It is small enough that
 * blocking the parser for it costs less than the flash it prevents.
 *
 * Wrapped in try/catch because reading localStorage throws outright when a
 * browser is set to block site data, and a theme preference is not worth
 * breaking the page over.
 */
export const THEME_SCRIPT = `(function(){try{
var s=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
var d=s==="dark"||(s!=="light"&&window.matchMedia(${JSON.stringify(DARK_QUERY)}).matches);
document.documentElement.classList.toggle("dark",d);
}catch(e){}})();`;

/** Whether a setting means dark right now. */
export function resolvesToDark(setting: ThemeSetting): boolean {
  if (setting === "system") return window.matchMedia(DARK_QUERY).matches;
  return setting === "dark";
}

export function readThemeSetting(): ThemeSetting {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Blocked storage is not an error worth surfacing; fall back to system.
  }
  return "system";
}

export function writeThemeSetting(setting: ThemeSetting): void {
  try {
    if (setting === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, setting);
  } catch {
    // The setting still applies to this page; it just will not be
    // remembered, which is better than refusing to switch at all.
  }
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

/** The next setting when the control is pressed. */
export function nextSetting(setting: ThemeSetting): ThemeSetting {
  if (setting === "system") return "light";
  return setting === "light" ? "dark" : "system";
}
