/**
 * Web app manifest.
 *
 * Present so the dashboard can be installed to a phone's home screen,
 * which is how it is opened most often: a rate check before answering a
 * bank happens on a phone, not at a desk.
 *
 * Product identity only, like every other metadata surface here.
 */

import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "CreditRadar",
    short_name: "CreditRadar",
    description: "Inteligência de crédito pessoal para o mercado brasileiro",
    lang: "pt-BR",
    start_url: "/",
    display: "standalone",
    // Matches --background in each theme, so the splash screen and the
    // browser chrome do not sit next to a slightly different page.
    background_color: "#ffffff",
    theme_color: "#ffffff",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
