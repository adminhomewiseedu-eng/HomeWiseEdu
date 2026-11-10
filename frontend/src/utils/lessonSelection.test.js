import test from 'node:test';
import assert from 'node:assert/strict';
import { filterSessions, prioritizedAssignments, weekLabel } from './lessonSelection.js';

const sessions = [{ subject_id: 1, unit_id: 1, curriculum_week: 10 }, { subject_id: 1, unit_id: 2, curriculum_week: null }, { subject_id: 2, unit_id: 3, curriculum_week: 10 }];
test('subject/week filters expose authored Week 10 and honest unknown weeks', () => {
  assert.deepEqual(filterSessions(sessions, '1', '10'), [sessions[0]]);
  assert.deepEqual(filterSessions(sessions, '', 'unknown'), [sessions[1]]);
  assert.equal(weekLabel(null), 'Week not supplied');
  assert.equal(weekLabel(10), 'Week 10');
  assert.equal(sessions[1].curriculum_week, null);
});
test('unit selection works without authored weeks and does not infer week numbers', () => {
  assert.deepEqual(filterSessions(sessions, '1', '', '2'), [sessions[1]]);
  assert.deepEqual(filterSessions(sessions, '1', 'unknown', '2'), [sessions[1]]);
  assert.deepEqual(filterSessions(sessions, '2', '', '2'), []);
  assert.equal(sessions[1].curriculum_week, null);
});
test('outstanding parent assignments prioritize due dates and priority without hiding student choices', () => {
  const a = [
    { assignment_id: 1, scheduled_date: '2026-11-10', priority: 5, status: 'not_started' },
    { assignment_id: 2, scheduled_date: '2026-11-10', priority: 0, status: 'in_progress' },
    { assignment_id: 3, scheduled_date: '2026-11-09', priority: 0, status: 'completed' },
    { assignment_id: 4, scheduled_date: '2026-11-11', priority: 0, status: 'not_started' },
  ];
  assert.deepEqual(prioritizedAssignments(a, '2026-11-10').map(x => x.assignment_id), [2, 1, 4]);
  assert.equal(a.length, 4);
  assert.equal(filterSessions(sessions).length, 3);
});
