import { test } from 'node:test';
import assert from 'node:assert/strict';
import { platformLabel } from '../src/utils/platform.ts';

test('known numeric/text platform values are preserved', () => {
  assert.equal(platformLabel('31', 'KNOWN', 'jr_odekake'), '31');
  assert.equal(platformLabel('4A', 'KNOWN', 'yahoo'), '4A');
  assert.equal(platformLabel(0, 'KNOWN', 'jr_odekake'), '0');
});

test('successful omission and lookup failure have different truthful labels', () => {
  assert.equal(platformLabel('', 'SOURCE_NOT_PROVIDED', 'jr_odekake'), '공식 정보 미제공');
  assert.equal(platformLabel('', 'SOURCE_NOT_PROVIDED', 'yahoo'), '출처 정보 미제공');
  assert.equal(platformLabel('', 'LOOKUP_FAILED', 'jr_odekake'), '조회 실패');
  assert.equal(platformLabel('31', 'LOOKUP_FAILED', 'jr_odekake'), '조회 실패');
});

test('legacy blank cannot establish successful source omission', () => {
  assert.equal(platformLabel('', undefined, 'jr_odekake'), '조회 실패');
  assert.equal(platformLabel('31', undefined, 'jr_odekake'), '31');
});
