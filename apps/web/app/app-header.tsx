import { Logo } from "@/components/site/logo";

/** The dark top bar used on the signed-in pages. */
export function AppHeader({ children }: { children?: React.ReactNode }) {
  return (
    <header className="dark">
      <div className="wrap topbar">
        <a href="/" className="logo" aria-label="IkonetU home"><Logo variant="navy" height={30} /></a>
        {children ? <nav aria-label="Account" className="nav">{children}</nav> : null}
      </div>
    </header>
  );
}
