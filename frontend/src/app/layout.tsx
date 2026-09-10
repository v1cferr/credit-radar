import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppSidebar } from "@/components/app-shell/app-sidebar";
import { MobileTabBar } from "@/components/app-shell/mobile-tab-bar";
import { TITLE_TEMPLATE } from "@/components/app-shell/section-metadata";
import { THEME_SCRIPT } from "@/components/app-shell/theme";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-mono", subsets: ["latin"] });

const DESCRIPTION = "Inteligência de crédito pessoal para o mercado brasileiro";

/**
 * Metadata carries the product's identity and nothing else.
 *
 * Every field here is a constant. A title, a description, an Open Graph tag
 * and a manifest are quoted verbatim by whatever renders a link preview, so
 * none of them may contain a score, a balance, a limit, a CPF or a
 * collection time -- not even a hint of one, such as "3 dívidas em aberto".
 * Sections contribute their own name through the template and nothing more.
 */
export const metadata: Metadata = {
  title: { default: "CreditRadar", template: TITLE_TEMPLATE },
  description: DESCRIPTION,
  applicationName: "CreditRadar",
  // A private, single-user application over sensitive financial data. It
  // must never be indexed, and `nocache` also keeps a search engine from
  // holding a copy of a page it should not have fetched at all.
  robots: { index: false, follow: false, nocache: true },
  openGraph: {
    type: "website",
    siteName: "CreditRadar",
    title: "CreditRadar",
    description: DESCRIPTION,
    locale: "pt_BR",
  },
};

export const viewport: Viewport = {
  // Both themes declared, matching --background in each, so the browser
  // chrome does not frame the page in the wrong colour.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
  colorScheme: "light dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // The font variables belong on the root element, not on the body. The
    // `font-sans` utility is applied to <html>, so a variable defined one
    // level down does not resolve there: the declaration is invalid, and
    // the whole document falls back to the browser's default serif. That
    // is how this application shipped every page in Times New Roman.
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased">
        {/* First thing in the document, and blocking: it resolves the theme
            before anything paints. Deferred, the first frame would be light
            and then flip, which on a dashboard opened at night is a white
            flash in a dark room. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <TooltipProvider>
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
              {/* Clears the fixed tab bar, so the last row of a table is
                  not left permanently under it. */}
              <div className="pb-14 md:pb-0">{children}</div>
            </SidebarInset>
            <MobileTabBar />
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
