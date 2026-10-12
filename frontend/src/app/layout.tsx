import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { DashboardShell } from "@/components/customer-voice/shell";

export const metadata: Metadata = {
  title: { default: "Customer Voice", template: "%s · Customer Voice" },
  applicationName: "Customer Voice",
  manifest: "/manifest.webmanifest",
  description: "Müşteri yorumlarına dayalı analiz, rating ve memnuniyet içgörüleri.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr" suppressHydrationWarning><body>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <DashboardShell>{children}</DashboardShell>
    </ThemeProvider>
  </body></html>;
}
