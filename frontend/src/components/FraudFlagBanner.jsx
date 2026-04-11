/**
 * KIRA — Fraud Flag Banner Component
 *
 * Conditional warning banner displayed only when fraud detection
 * flags the assessment (is_flagged: true). Lists specific flags.
 *
 * Owner: Frontend Lead
 * Phase: 5.7
 *
 * Props:
 *   isFlagged (boolean) — Whether to show the banner
 *   fraudScore (number) — 0-1 fraud score
 *   flags (array) — List of specific fraud flag strings
 */

export default function FraudFlagBanner({ isFlagged, fraudScore, flags = [] }) {
  // Don't render if not flagged
  if (!isFlagged) return null;

  // TODO: Implement fraud warning banner with:
  //   - Yellow/amber warning banner (professional, not alarming)
  //   - "Assessment Flagged for Review" heading
  //   - Fraud score display
  //   - List of specific flags in plain language
  //   - Note: "This assessment has been flagged for manual review"

  return (
    <div>
      {/* TODO: Implement fraud flag banner UI */}
      <p>⚠️ Assessment flagged for review</p>
    </div>
  );
}
