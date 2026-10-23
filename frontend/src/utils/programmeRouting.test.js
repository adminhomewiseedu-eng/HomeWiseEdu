import test from 'node:test';
import assert from 'node:assert/strict';
import { bibleSubjectsOnly, dashboardFor, isBibleUser, mayOpenProgrammeRoute } from './programmeRouting.js';

test('routes parents and students by trusted programme and role', () => {
  assert.equal(dashboardFor({ role: 'parent', programme: 'bible_study' }), '/bible-study/parent');
  assert.equal(dashboardFor({ role: 'student', programme: 'bible_study' }), '/bible-study/student');
  assert.equal(dashboardFor({ role: 'parent', programme: 'homeschool' }), '/parent');
  assert.equal(dashboardFor({ role: 'student', programme: 'homeschool' }), '/student');
  assert.equal(dashboardFor({ role: 'admin' }), '/admin');
});

test('denies direct cross-programme dashboard rendering', () => {
  const bible = { role: 'parent', programme: 'bible_study' };
  const homeschool = { role: 'parent', programme: 'homeschool' };
  assert.equal(mayOpenProgrammeRoute(bible, 'homeschool'), false);
  assert.equal(mayOpenProgrammeRoute(bible, 'bible_study'), true);
  assert.equal(mayOpenProgrammeRoute(homeschool, 'bible_study'), false);
});

test('Bible subject visibility excludes every homeschool subject', () => {
  const visible = bibleSubjectsOnly([
    { slug: 'mathematics', subject: 'Mathematics' },
    { slug: 'understanding-the-word', subject: 'Understanding The Word' },
    { slug: 'science', subject: 'Science' },
  ]);
  assert.deepEqual(visible.map((item) => item.slug), ['understanding-the-word']);
  assert.equal(isBibleUser({ programme: 'bible_study' }), true);
});
