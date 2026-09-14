import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const screen = fs.readFileSync(new URL('../components/templates/AdminDashboardScreen.jsx', import.meta.url), 'utf8');
const api = fs.readFileSync(new URL('../services/api.js', import.meta.url), 'utf8');

test('curriculum detail exposes archive and dependency-gated permanent deletion', () => {
  assert.match(screen, /getLessonDependencies/);
  assert.match(screen, /Permanent deletion is blocked/);
  assert.match(screen, /Archive instead/);
  assert.match(screen, /Confirm Permanent Delete/);
  assert.match(screen, /window\.confirm/);
  assert.match(api, /\/dependencies/);
  assert.match(api, /deleteLesson/);
});

test('curriculum UI distinguishes archived and quiz-review-required lessons', () => {
  assert.match(screen, /<option>archived<\/option>/);
  assert.match(screen, /Quiz review required/);
  assert.match(screen, /Review the approved quiz for alignment/);
});

test('curriculum UI displays cadence-aware session counts', () => {
  assert.match(screen, /lesson\.expected_days/);
  assert.match(screen, /Weekly Lesson/);
  assert.match(screen, /Multi-day/);
  assert.doesNotMatch(screen, /lesson\.days\}\/3/);
});
