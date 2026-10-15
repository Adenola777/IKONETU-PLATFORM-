import Link from "next/link";
import { Logo } from "./logo";
import "./sign-in.css";

/** The frame of the sign-in pages: the lockup, a way back home, and one narrow column. */
export function SignInFrame({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <div className="site pg-signin">
      <div className="page">
        <a className="skip" href="#main">Skip to content</a>
        <header className="si-hdr">
          <div className="si-hdr-in">
            <Link href="/" aria-label="IkonetU home"><Logo variant="default" height={34} /></Link>
            <Link href="/">Back to the home page</Link>
          </div>
        </header>
        <main id="main" className="si-main">
          {label ? <p className="si-lbl">{label}</p> : null}
          {children}
        </main>
      </div>
    </div>
  );
}
