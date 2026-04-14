export const ACTIVE_LOAN_STATUSES = ['approved', 'disbursed', 'monitoring', 'restructured'];

export function getCaseNextAction(caseItem) {
  switch (caseItem?.status) {
    case 'draft':
      return 'Complete borrower intake';
    case 'submitted':
      return 'Start underwriting review';
    case 'under_review':
      return 'Approve, decline, or request override';
    case 'approved':
      return 'Prepare for disbursement';
    case 'disbursed':
      return 'Start monitoring cadence';
    case 'monitoring':
      return 'Collect fresh statement upload';
    case 'restructured':
      return 'Track recovery and next review';
    case 'closed':
      return 'No action pending';
    default:
      return 'Review case';
  }
}

export function formatCurrency(amount) {
  if (amount == null) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}
