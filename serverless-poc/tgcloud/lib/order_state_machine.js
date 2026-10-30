// Port of services/order_state_machine.py (financial invariants, NO execution).
// Every monetary status change must use this policy AND a database transaction.
// Storage-level constraints, idempotency and operator authorization remain required.
const POLICY = Object.freeze({
  pending: ['payment_pending', 'payment_submitted', 'under_review', 'confirmed', 'cancelled', 'rejected', 'expired', 'failed'],
  payment_pending: ['payment_submitted', 'under_review', 'cancelled', 'expired', 'failed'],
  payment_submitted: ['under_review', 'confirmed', 'approved', 'cancelled', 'rejected', 'failed'],
  under_review: ['approved', 'confirmed', 'cancelled', 'rejected', 'failed'],
  confirmed: ['processing', 'completed', 'cancelled', 'failed'],
  approved: ['processing', 'cancelled', 'failed'],
  processing: ['completed', 'failed', 'cancelled'],
  completed: [], cancelled: [], rejected: [], expired: [], failed: [],
});
const TERMINAL = new Set(['completed', 'cancelled', 'rejected', 'expired', 'failed']);

export function canTransition(from, to) {
  return Object.hasOwn(POLICY, from) &&
    (from === to || POLICY[from].includes(to));
}
export function assertTransition(from, to) {
  if (!canTransition(from, to)) {
    throw new Error(`Invalid USDT order status transition: ${String(from)} -> ${String(to)}`);
  }
}
export function isTerminal(status) {
  return TERMINAL.has(status);
}
export const ALL_ORDER_STATUSES = Object.freeze(Object.keys(POLICY));
