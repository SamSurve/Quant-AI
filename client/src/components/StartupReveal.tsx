/**
 * Research Observatory visual contract: a single restrained 1.2-second mark
 * and price-line reveal. It honors reduced motion and never blocks research.
 */

import { useEffect, useState } from "react";

export function StartupReveal() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(() => setVisible(false), reducedMotion ? 0 : 1180);
    return () => window.clearTimeout(timer);
  }, []);
  if (!visible) return null;
  return (
    <div className="startup-reveal" aria-hidden="true">
      <div className="startup-reveal__content">
        <img src="/assets/analysts-ledger-logo.png" alt="" className="startup-reveal__mark" />
        <p className="startup-reveal__name">QUANTAI</p>
        <svg className="startup-reveal__trace" viewBox="0 0 260 54" fill="none" preserveAspectRatio="none"><path d="M0 43H32L50 35L75 39L101 19L127 31L154 24L179 29L203 8L230 17L260 5" /></svg>
        <p className="startup-reveal__note">Research. Understand. Decide.</p>
      </div>
    </div>
  );
}
