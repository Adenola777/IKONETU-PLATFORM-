import type { MetadataRoute } from "next";
import { PUBLIC_PAGES } from "@/lib/pages";
import { SITE_URL } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  return Object.values(PUBLIC_PAGES).map((page) => ({ url: page.path === "/" ? SITE_URL : `${SITE_URL}${page.path}` }));
}
