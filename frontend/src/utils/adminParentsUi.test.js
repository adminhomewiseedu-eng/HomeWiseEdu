import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyParentsMessage, nextParentStatus, parentPageCount, parentStatusAction } from './adminParentsUi.js';

test('parent pagination is stable for empty and populated results', () => {
  assert.equal(parentPageCount(0, 20), 1);
  assert.equal(parentPageCount(41, 20), 3);
});

test('parent empty state distinguishes an empty dataset from search results', () => {
  assert.equal(emptyParentsMessage(''), 'No parents found.');
  assert.equal(emptyParentsMessage('Ada'), 'Search returned no results.');
});

test('parent status action toggles only between supported states', () => {
  assert.equal(nextParentStatus('active'), 'suspended');
  assert.equal(parentStatusAction('active'), 'Suspend');
  assert.equal(nextParentStatus('suspended'), 'active');
  assert.equal(parentStatusAction('suspended'), 'Reactivate');
});
