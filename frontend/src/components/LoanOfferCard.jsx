/**
 * KIRA — Loan Offer Card Component
 *
 * Displays loan recommendation: range, tenure, EMI, eligibility.
 *
 * Owner: Frontend Lead
 * Phase: 5.6
 *
 * Props:
 *   eligible (boolean) — Whether the store qualifies
 *   loanRange (object) — { min, max } in INR
 *   suggestedTenure (number) — Months
 *   estimatedEmi (number) — Monthly EMI in INR
 *   emiToIncomeRatio (number) — 0-1
 */

export default function LoanOfferCard({ eligible, loanRange, suggestedTenure, estimatedEmi, emiToIncomeRatio }) {
  // TODO: Implement loan offer display with:
  //   - Eligibility status (eligible / not eligible)
  //   - Loan range: ₹min — ₹max
  //   - Suggested tenure in months
  //   - EMI estimate display
  //   - EMI-to-income ratio indicator
  //   - If not eligible, show reason (fraud flagged / very high risk)

  return (
    <div>
      {/* TODO: Implement loan offer card UI */}
      <p>Loan Offer Card</p>
    </div>
  );
}
