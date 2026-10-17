import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

/** Search engines may read the public pages. The sign-in steps, the signed-in pages and the API stay out. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/auth/", "/signin", "/onboarding", "/dashboard", "/investor/", "/introductions/", "/admin", "/suspended"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
