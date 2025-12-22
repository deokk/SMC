export default function Header() {
  return (
    <header className="mp-header" aria-label="SMC header">
      <div className="mp-headerPill">
        <div className="mp-logo">
          <div className="mp-logoBadge">
            <img src="/logo.svg" alt="SMC" className="mp-logoBadgeImg" />
          </div>
          <span className="mp-logoText">SMC</span>
        </div>
      </div>
    </header>
  );
}