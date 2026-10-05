import { LEAGUE_THRESHOLDS } from "@ikonetu/score-engine";
import { leagueColors } from "@ikonetu/ui-tokens";
import { WaitlistForm } from "./waitlist-form";

const fmt = (n: number) => n.toLocaleString("en-GB");

const LEAGUES = [
  { name: "Early", color: leagueColors.EARLY, from: 0, to: LEAGUE_THRESHOLDS.RISING - 1, text: "You have an idea or a first version and are gathering proof." },
  { name: "Rising", color: leagueColors.RISING, from: LEAGUE_THRESHOLDS.RISING, to: LEAGUE_THRESHOLDS.INVESTABLE - 1, text: "You have customers or a team, registered or not." },
  { name: "Investable", color: leagueColors.INVESTABLE, from: LEAGUE_THRESHOLDS.INVESTABLE, to: LEAGUE_THRESHOLDS.ELITE - 1, text: "Your registration, revenue and team are verified." },
  { name: "Elite", color: leagueColors.ELITE, from: LEAGUE_THRESHOLDS.ELITE, to: 1000, text: "Your business is proven on every measure we check." },
];

const STEPS = [
  { title: "Build", text: "You post what you ship each week and follow founders at your stage." },
  { title: "Submit evidence", text: "You upload documents or connect your company registry or bank, and we check each claim." },
  { title: "Earn your score", text: "Every approved item adds points to a score out of 1,000. Claims without evidence add nothing." },
  { title: "Get found", text: "Investors, mentors and programmes browse the leagues and ask to meet the founders who are ready." },
];

const REWARDS = [
  { title: "Investor introductions", text: "Winners in the Investable and Elite leagues meet investors directly." },
  { title: "Mentor matching", text: "Winners get priority with mentors who know their sector." },
  { title: "Accelerator referrals", text: "We introduce winners to programmes when their applications open." },
  { title: "Startup credits guide", text: "Every verified founder gets step-by-step help to claim free cloud and software credits." },
];

const EXAMPLE_BARS = [
  { label: "Company registration", width: 100, status: "Verified" },
  { label: "Revenue, last 12 months", width: 72, status: "Verified" },
  { label: "Customer evidence", width: 40, status: "In review" },
];

export default function Home() {
  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="dark">
        <div className="wrap topbar">
          <a href="#top" className="logo" aria-label="IkonetU home">Ikonet<span>U</span></a>
          <nav aria-label="Main" className="nav">
            <a href="#how">How it works</a>
            <a href="#leagues">Leagues</a>
            <a href="#rewards">Rewards</a>
            <a href="#capital">Investors and mentors</a>
            <a href="#waitlist" className="btn btn-orange">Join the waitlist</a>
          </nav>
        </div>
        <div id="top" className="wrap hero">
          <div className="hero-copy">
            <p className="eyebrow">Season 1 · Nigeria, Ghana and Kenya</p>
            <h1 className="display">Build your startup and prove every step of it.</h1>
            <p className="hero-lede">
              IkonetU gives African founders a verified score. You submit evidence of what you have built, we check it,
              and your score places you in a league that investors, mentors and programmes can trust.
            </p>
            <div className="ctas">
              <a href="#waitlist" className="btn btn-orange">Join the waitlist</a>
              <a href="#how" className="btn btn-ghost">See how scoring works</a>
            </div>
          </div>
          <div className="hero-card-wrap">
            <figure className="score-card" aria-label="Example IkonetU Score card" style={{ margin: 0 }}>
              <div className="score-card-head">
                <span>IkonetU Score</span>
                <span className="pill">Investable league</span>
              </div>
              <div className="score-num">
                <strong>642</strong>
                <span>of 1,000</span>
              </div>
              <ul className="bars">
                {EXAMPLE_BARS.map((b) => (
                  <li key={b.label}>
                    <div className="bar-label">
                      <span>{b.label}</span>
                      <span className={b.status === "Verified" ? "ok" : "pending"}>{b.status}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${b.width}%`, background: b.status === "Verified" ? undefined : "var(--orange)" }} />
                    </div>
                  </li>
                ))}
              </ul>
              <figcaption className="caption">Example profile</figcaption>
            </figure>
          </div>
        </div>
      </header>

      <main id="main">
        <section id="how" className="section">
          <div className="wrap">
            <h2 className="title">How IkonetU works</h2>
            <p className="lede">Your score only rises when your evidence checks out. That rule is why the people who browse IkonetU can trust what they see.</p>
            <ol className="grid" style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {STEPS.map((s, i) => (
                <li key={s.title} className="card">
                  <p className="step">Step {i + 1}</p>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="leagues" className="section tint">
          <div className="wrap">
            <h2 className="title">Four leagues, one score</h2>
            <p className="lede">Your verified score decides your league. You move up the moment approved evidence lifts you past the next line.</p>
            <div className="grid" style={{ gap: 20 }}>
              {LEAGUES.map((l) => (
                <div key={l.name} className="card league" style={{ borderTopColor: l.color }}>
                  <h3>{l.name}</h3>
                  <p className="range">{fmt(l.from)} to {fmt(l.to)}</p>
                  <p>{l.text}</p>
                </div>
              ))}
            </div>
            <div className="split">
              <div className="card card-navy">
                <h3>Effort counts too</h3>
                <p>
                  You earn Momentum points for weekly updates, approved evidence, streaks and helping other founders.
                  Momentum ranks you inside your league and decides the weekly and season winners. It never moves you between leagues.
                </p>
              </div>
              <div className="card">
                <h3>Seasons and weekly rounds</h3>
                <p>Each season runs for 13 weeks. Every Monday you join a round with 20 to 30 founders at your level, and the results arrive the following Monday.</p>
              </div>
            </div>
          </div>
        </section>

        <section id="rewards" className="section">
          <div className="wrap">
            <h2 className="title">What winners receive</h2>
            <p className="lede" style={{ marginBottom: 40 }}>Season winners in each league receive rewards that help them grow. Every verified founder also gets help claiming free startup credits.</p>
            <div className="grid" style={{ gap: 20 }}>
              {REWARDS.map((r) => (
                <div key={r.title} className="card" style={{ padding: 24 }}>
                  <h3 style={{ fontSize: 19 }}>{r.title}</h3>
                  <p style={{ fontSize: 15 }}>{r.text}</p>
                </div>
              ))}
            </div>
            <p className="note">We announce sponsor prizes only after each sponsor agreement is signed.</p>
          </div>
        </section>

        <section className="dark">
          <div className="wrap countries">
            <div>
              <h2 className="title">Your score counts for your country</h2>
              <p>The Country Championship ranks Nigeria, Ghana and Kenya by the average score of their verified founders. The top founder in each country earns the Country Champion badge.</p>
            </div>
            <div className="chips">
              <span>Nigeria</span>
              <span>Ghana</span>
              <span>Kenya</span>
            </div>
          </div>
        </section>

        <section id="capital" className="section">
          <div className="wrap">
            <h2 className="title" style={{ marginBottom: 40 }}>For investors and mentors</h2>
            <div className="split" style={{ marginTop: 0 }}>
              <div className="card" style={{ padding: 32 }}>
                <h3>Investors</h3>
                <p style={{ marginBottom: 16 }}>
                  You filter founders by league, country, sector and stage, and you see how each claim was verified.
                  When a founder fits, you request an introduction and the founder decides.
                </p>
                <p style={{ fontSize: 14, color: "var(--text-muted)" }}>IkonetU makes introductions. It does not arrange investments or handle money.</p>
              </div>
              <div className="card" style={{ padding: 32 }}>
                <h3>Mentors</h3>
                <p>You see where each founder&apos;s score is weakest, so you can offer help where it will count. Founders accept the offers they want.</p>
              </div>
            </div>
          </div>
        </section>

        <section id="waitlist" className="section tint">
          <div className="wrap form-wrap">
            <h2 className="title" style={{ marginBottom: 12 }}>Join the waitlist</h2>
            <p className="lede" style={{ marginBottom: 36 }}>We will tell you when Season 1 opens in your country.</p>
            <WaitlistForm />
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="wrap">
          <p>IkonetU Technology Limited is registered in England and Wales, company number 17110122.</p>
          <nav aria-label="Footer">
            <a href="/privacy">Privacy notice</a>
            <a href="/privacy#contact">Contact</a>
          </nav>
        </div>
      </footer>
    </>
  );
}
