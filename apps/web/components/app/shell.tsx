import Link from "next/link";
import { signOut } from "@/app/dashboard/actions";
import { Logo } from "@/components/site/logo";
import "./app.css";

export type Section =
  | "overview" | "pitch" | "evidence" | "updates" | "introductions" | "preview"
  | "discover" | "requests" | "profile"
  | "queue" | "investors"
  | "";

const NAV: Record<string, { key: Section; href: string; label: string }[]> = {
  founder: [
    { key: "overview", href: "/dashboard", label: "Overview" },
    { key: "pitch", href: "/dashboard/pitch", label: "Pitch" },
    { key: "evidence", href: "/dashboard/evidence", label: "Evidence" },
    { key: "updates", href: "/dashboard/updates", label: "Updates" },
    { key: "introductions", href: "/dashboard/introductions", label: "Introductions" },
    { key: "preview", href: "/dashboard/preview", label: "What investors see" },
  ],
  investor: [
    { key: "discover", href: "/investor", label: "Discover founders" },
    { key: "requests", href: "/investor/introductions", label: "Introductions" },
    { key: "profile", href: "/investor/profile", label: "Your profile" },
  ],
  reviewer: [{ key: "queue", href: "/admin/evidence", label: "Evidence to review" }],
  admin: [
    { key: "queue", href: "/admin/evidence", label: "Evidence to review" },
    { key: "investors", href: "/admin/investors", label: "Investors" },
  ],
};

/**
 * The frame of every signed-in page: the lockup, the sections for the
 * person's role, and sign out. It uses the website's shared styles.
 */
export function AppShell({
  role,
  current = "",
  children,
}: {
  role?: "founder" | "investor" | "reviewer" | "admin" | "none";
  current?: Section;
  children: React.ReactNode;
}) {
  const links = role && role !== "none" ? NAV[role] ?? [] : [];
  const accent = role === "investor" ? "app-i" : "app-f";
  return (
    <div className={`site pg-app ${accent}`}>
      <div className="page">
        <a className="skip" href="#main">Skip to content</a>
        <header className="app-hdr">
          <div className="app-hdr-in">
            <Link href="/" aria-label="IkonetU home" className="app-logo"><Logo variant="default" height={30} /></Link>
            <form action={signOut}>
              <button type="submit" className="btn btn-n btn-sm">Sign out</button>
            </form>
          </div>
          {links.length > 0 && (
            <nav aria-label="Sections" className="app-nav">
              <ul>
                {links.map((l) => (
                  <li key={l.key}>
                    <Link href={l.href} aria-current={l.key === current ? "page" : undefined}>{l.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </header>
        <main id="main" className="app-main">{children}</main>
      </div>
    </div>
  );
}
