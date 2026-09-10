"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Radar } from "lucide-react";

/**
 * The full navigation, permanent on a desktop viewport and a drawer on a
 * phone.
 *
 * Links do not prefetch. Every route here is server-rendered on demand
 * against the backend, so viewport prefetching means that opening any page
 * asks the server to render all thirteen others -- including the market
 * page, which fetches years of daily observations. The cost is paid on
 * every page view, on a phone connection too, for routes the reader may
 * never open. Fetching on navigation is the right trade for a dashboard
 * whose pages are individually expensive and individually rare.
 */

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { NAVIGATION } from "@/components/app-shell/navigation";

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/" prefetch={false} />}
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Radar className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">CreditRadar</span>
                <span className="truncate text-xs text-muted-foreground">
                  Inteligência de crédito pessoal
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {NAVIGATION.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      isActive={pathname === item.href}
                      tooltip={item.title}
                      className={
                        item.implemented ? undefined : "text-muted-foreground"
                      }
                      render={<Link href={item.href} prefetch={false} />}
                    >
                      <item.icon />
                      <span>{item.title}</span>
                      {item.implemented ? null : (
                        <span className="sr-only"> (seção planejada)</span>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <p className="px-2 text-[0.65rem] leading-snug text-muted-foreground group-data-[collapsible=icon]:hidden">
          Observa e explica. Nunca aceita acordo, movimenta dinheiro nem
          contrata crédito.
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
