"use client";

/**
 * Cycles the theme between system, light and dark.
 *
 * One button rather than a menu: three states are few enough to cycle
 * through, and this control sits in a header already carrying a title, a
 * navigation trigger and whatever the page itself needs.
 *
 * The icon reports the setting, not the resulting colour -- a monitor for
 * "follow the system", a sun for light, a moon for dark -- because those
 * are different facts, and a reader following the system wants to see that
 * they are.
 */

import * as React from "react";
import { Monitor, Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DARK_QUERY,
  nextSetting,
  writeThemeSetting,
  type ThemeSetting,
} from "@/components/app-shell/theme";
import { useThemeSetting } from "@/hooks/use-theme-setting";

const ICONS: Record<ThemeSetting, typeof Monitor> = {
  system: Monitor,
  light: Sun,
  dark: Moon,
};

const LABELS: Record<ThemeSetting, string> = {
  system: "Tema: seguindo o sistema",
  light: "Tema: claro",
  dark: "Tema: escuro",
};

export function ThemeToggle() {
  const setting = useThemeSetting();

  // Applies the setting to the document, and keeps following the system
  // while that is what was chosen. Writing the class here rather than in
  // the click handler means the setting has exactly one consequence, no
  // matter which of the three sources changed it.
  React.useEffect(() => {
    const query = window.matchMedia(DARK_QUERY);
    const apply = () =>
      document.documentElement.classList.toggle(
        "dark",
        setting === "system" ? query.matches : setting === "dark",
      );

    apply();
    if (setting !== "system") return;

    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, [setting]);

  const Icon = ICONS[setting];
  const label = LABELS[setting];

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            // Announced instead of the icon, which says nothing on its own.
            aria-label={`${label}. Alternar tema.`}
            onClick={() => writeThemeSetting(nextSetting(setting))}
          >
            <Icon className="size-4" />
          </Button>
        }
      />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
