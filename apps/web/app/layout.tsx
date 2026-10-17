import type { Metadata, Viewport } from "next";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { SideProvider } from "@/components/site/side";
import { PUBLIC_PAGES } from "@/lib/pages";
import { SITE_URL } from "@/lib/site";
import "./globals.css";
import "./site.css";

// next/font downloads both fonts at build time and serves them from this site,
// so a visitor's browser never asks Google for them. It also sizes the fallback
// fonts to match, so text does not jump when the fonts arrive.
const serif = Fraunces({ subsets: ["latin", "latin-ext", "vietnamese"], weight: "variable", axes: ["opsz"], display: "swap", variable: "--font-serif" });
const sans = Plus_Jakarta_Sans({ subsets: ["latin", "latin-ext", "vietnamese"], weight: ["400", "600"], display: "swap", variable: "--font-sans" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: PUBLIC_PAGES.home.title, template: "%s | IkonetU" },
  description: PUBLIC_PAGES.home.description,
  applicationName: "IkonetU",
  openGraph: { siteName: "IkonetU", type: "website", locale: "en_GB" },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = { themeColor: "#FFFFFF", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB" className={`${serif.variable} ${sans.variable}`}>
      <body>
        <SideProvider>{children}</SideProvider>
      </body>
    </html>
  );
}
