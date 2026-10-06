/** The dark top bar used on the sign-in and signed-in pages. */
export function AppHeader({ children }: { children?: React.ReactNode }) {
  return (
    <header className="dark">
      <div className="wrap topbar">
        <a href="/" className="logo" aria-label="IkonetU home">Ikonet<span>U</span></a>
        {children ? <nav aria-label="Account" className="nav">{children}</nav> : null}
      </div>
    </header>
  );
}
