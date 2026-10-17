import Link from "next/link";
import { SiteFooter } from "@/components/site/footer";
import { SiteHeader } from "@/components/site/header";

export const metadata = { title: "Page not found", robots: { index: false } };

export default function NotFound() {
  return (
    <div className="site">
      <div className="page">
        <SiteHeader current="" />
        <main id="main">
          <section aria-labelledby="nf-title">
            <div className="wrap narrow" style={{ paddingTop: 96, paddingBottom: 112 }}>
              <p className="lbl" style={{ marginBottom: 20 }}>Page not found</p>
              <h1 id="nf-title" className="h1">This page does not exist.</h1>
              <p className="lede" style={{ marginBottom: 32 }}>The address may be mistyped, or the page may have moved.</p>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "16px 32px" }}>
                <Link className="btn btn-f btn-lg" href="/">Go to the home page</Link>
                <Link className="tlink" href="/questions">Read the questions</Link>
              </div>
            </div>
          </section>
        </main>
        <SiteFooter />
      </div>
    </div>
  );
}
