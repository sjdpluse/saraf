import test from 'node:test';
import assert from 'node:assert/strict';
import { canTransition, assertTransition, isTerminal, ALL_ORDER_STATUSES } from '../tgcloud/lib/order_state_machine.js';
test('normal order path: pending → confirmed → processing → completed', () => {
  for (const [from, to] of [['pending','confirmed'], ['confirmed','processing'], ['processing','completed']])
    assert.equal(canTransition(from,to), true);
});
test('terminal statuses cannot be reopened', () => {
  for (const status of ['completed','cancelled','rejected','expired','failed']) {
    assert.equal(isTerminal(status), true);
    assert.equal(canTransition(status,'pending'), false);
    assert.throws(() => assertTransition(status,'pending'));
  }
});
test('idempotent no-op transitions remain legal', () => {
  for (const status of ALL_ORDER_STATUSES) assert.equal(canTransition(status,status), true);
});
test('unknown statuses are rejected', () => {
  assert.equal(canTransition('unknown','completed'), false);
});
