/**
 * KIRA — Home Page (Landing)
 *
 * Landing page with product framing, value proposition,
 * "Start Assessment" CTA, and how-it-works section.
 *
 * Owner: Frontend Lead
 * Phase: 5.1
 */

import { Link } from 'react-router-dom';

export default function Home() {
  // TODO: Implement landing page with:
  //   - Hero section with KIRA branding and one-liner
  //   - "Start Assessment" CTA button linking to /assess
  //   - How it works section (3 steps: Upload Images → Enter Location → Get Assessment)
  //   - Key stats section (13M kirana stores, <30s assessment, zero paperwork)
  //   - Professional, clean design with KIRA branding
  return (
    <div>
      <h1>KIRA — Kirana Intelligence &amp; Risk Assessment</h1>
      {/* TODO: Build landing page */}
      <Link to="/assess">Start Assessment</Link>
    </div>
  );
}
