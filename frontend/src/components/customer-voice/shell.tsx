"use client";
import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconChartBar, IconMessageCircle, IconSparkles, IconDatabase, IconLayersIntersect, IconExternalLink } from "@tabler/icons-react";
import { BrandMark } from "./brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Sidebar, SidebarProvider, SidebarHeader, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarInset, SidebarTrigger, useSidebar } from "@/components/ui/sidebar";
import { api, emptyFilters, type Filters, type Options, type Sentiment } from "@/lib/api";
const FilterContext = createContext<{ filters: Filters; setFilters: React.Dispatch<React.SetStateAction<Filters>> } | null>(null);
export function useFilters() { const context = useContext(FilterContext); if (!context) throw new Error("Missing filters provider"); return context; }
const navigation = [
  { title: "Overview", href: "/", icon: IconChartBar },
  { title: "Yorum Gezgini", href: "/reviews", icon: IconMessageCircle },
  { title: "Şikâyet Temaları", href: "/themes", icon: IconLayersIntersect, IconExternalLink },
  { title: "AI İçgörüleri", href: "/insights", icon: IconSparkles },
  { title: "Veri Kalitesi", href: "/data-quality", icon: IconDatabase },
];
function Navigation() {
  const pathname = usePathname(); const { setOpenMobile } = useSidebar();
  return <Sidebar collapsible="offcanvas">
    <SidebarHeader className="px-5 py-6"><Link href="/" className="flex items-center gap-3" onClick={() => setOpenMobile(false)}>
      <BrandMark className="size-9 shrink-0" />
      <span className="text-sm font-semibold">Customer Voice</span>
    </Link></SidebarHeader>
    <SidebarContent><SidebarGroup><SidebarGroupLabel>ANALİZLER</SidebarGroupLabel><SidebarMenu>
      {navigation.map(item => <SidebarMenuItem key={item.href}><SidebarMenuButton asChild isActive={pathname === item.href}>
        <Link href={item.href} aria-current={pathname === item.href ? "page" : undefined} onClick={() => setOpenMobile(false)}><item.icon /><span>{item.title}</span></Link>
      </SidebarMenuButton></SidebarMenuItem>)}
    </SidebarMenu></SidebarGroup></SidebarContent>
    <SidebarFooter className="border-t p-4"><a href="https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews" target="_blank" rel="noopener noreferrer" className="flex items-center justify-between gap-2 rounded-md px-2 py-2 text-xs text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-2 focus-visible:outline-primary"><span>Veri seti · Kaggle</span><IconExternalLink size={15} aria-hidden="true" /></a></SidebarFooter>

  </Sidebar>;
}
function FilterBar() {
  const { filters, setFilters } = useFilters();
  const [state, setState] = useState<{ department: string | null; data?: Options; error?: string }>();
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); const department = filters.department;
    api.options(department, controller.signal).then(result => {
      if (!controller.signal.aborted) setState({ department, data: result.data });
    }).catch(() => { if (!controller.signal.aborted) setState({ department, error: "Filtre seçenekleri yüklenemedi." }); });
    return () => controller.abort();
  }, [filters.department, retry]);
  const current = state?.department === filters.department ? state : undefined;
  const update = (field: keyof Filters, value: string) => setFilters(previous => ({ ...previous, [field]: value || null, ...(field === "department" ? { class_name: null } : {}) }));
  const selectClass = "h-9 w-full rounded-md border bg-background px-2 text-sm focus-visible:outline-2 focus-visible:outline-primary";
  return <section aria-label="Yorum filtreleri" className="rounded-xl border bg-card p-4">
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_.7fr_1fr_1.4fr_auto]">
      <label className="grid gap-1.5 text-xs font-medium">Departman<select aria-label="Departman" className={selectClass} value={filters.department || ""} onChange={e => update("department", e.target.value)}><option value="">Tüm departmanlar</option>{(state?.data?.departments || []).map(value => <option key={value}>{value}</option>)}{filters.department && !state?.data?.departments.includes(filters.department) && <option>{filters.department}</option>}</select></label>
      <label className="grid gap-1.5 text-xs font-medium">Ürün sınıfı<select aria-label="Ürün sınıfı" className={selectClass} disabled={!current?.data} value={filters.class_name || ""} onChange={e => update("class_name", e.target.value)}><option value="">Tüm ürün sınıfları</option>{current?.data?.classes.map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="grid gap-1.5 text-xs font-medium">Rating<select aria-label="Rating" className={selectClass} value={filters.rating || ""} onChange={e => setFilters(previous => ({ ...previous, rating: e.target.value ? Number(e.target.value) : null }))}><option value="">Tüm rating değerleri</option>{[1,2,3,4,5].map(value => <option key={value} value={value}>{value} yıldız</option>)}</select></label>
      <label className="grid gap-1.5 text-xs font-medium">Sentiment<select aria-label="Sentiment" className={selectClass} value={filters.sentiment || ""} onChange={e => setFilters(previous => ({ ...previous, sentiment: (e.target.value || null) as Sentiment | null }))}><option value="">Tüm tahminler</option>{["positive","neutral","negative","unknown"].map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="grid gap-1.5 text-xs font-medium">Yorumlarda ara<input aria-label="Yorumlarda ara" className={selectClass} maxLength={200} placeholder="Başlık veya yorumda ara…" value={filters.search || ""} onChange={e => update("search", e.target.value)} /></label>
      <Button variant="outline" className="self-end" onClick={() => setFilters({ ...emptyFilters })}>Filtreleri temizle</Button>
    </div>
    {current?.error && <p role="alert" className="mt-3 text-sm text-destructive">{current.error} <button className="underline" onClick={() => { setState(undefined); setRetry(value => value+1); }}>Yeniden dene</button></p>}
  </section>;
}
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<Filters>({ ...emptyFilters });
  return <FilterContext.Provider value={{ filters, setFilters }}><SidebarProvider>
    <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-background focus:p-3">İçeriğe geç</a>
    <Navigation /><SidebarInset className="min-w-0 bg-muted/25">
      <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background px-4 md:px-7"><div className="flex items-center gap-3"><SidebarTrigger aria-label="Menüyü aç/kapat" /><BrandMark className="size-7 shrink-0" /><span className="text-sm font-semibold">Customer Voice</span></div><ThemeToggle /></header>
      <div id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1500px] space-y-6 p-4 md:p-7"><FilterBar />{children}</div>
    </SidebarInset>
  </SidebarProvider></FilterContext.Provider>;
}
