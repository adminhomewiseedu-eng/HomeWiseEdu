// Requires the isolated backend fixture and local frontend. Never targets production.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const base = 'http://127.0.0.1:3012';
const artifacts = await fs.mkdtemp(path.join(os.tmpdir(), 'hwe-selection-browser-artifacts-'));
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const errors = [];
const consoleErrors = [];
const resourceDiagnostics = [];
const failures = [];
await context.route('**/*', route => {
  const url = new URL(route.request().url());
  return ['127.0.0.1', 'localhost'].includes(url.hostname) || url.protocol === 'data:' ? route.continue() : route.abort();
});
const page = await context.newPage();
page.on('pageerror', e => errors.push(e.message));
page.on('console', message => {
  if (!['error', 'warning', 'warn'].includes(message.type())) return;
  if (message.text().startsWith('Failed to load resource:')) resourceDiagnostics.push(message.text());
  else consoleErrors.push(message.text());
});
page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 400 && !(r.status() === 404 && r.url().endsWith('/profile/image'))) failures.push({ url: new URL(r.url()).pathname, status: r.status() }); });
async function login(email) {
  await page.goto(`${base}/login`);
  await page.getByPlaceholder('you@email.com').fill(email);
  await page.getByPlaceholder('Your password').fill('LocalPlanning123!');
  await page.getByRole('button', { name: 'Log in →', exact: true }).click();
}
async function fits() {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Page overflow');
}
try {
  await login('planning-parent@example.test');
  await page.waitForURL('**/parent');
  await page.getByLabel('Plan learning for').selectOption({ label: 'Planning child' });
  const plan = page.getByRole('region', { name: 'Plan learning', exact: true });
  await plan.getByText('Mathematics · Mathematics QA fixture', { exact: true }).first().waitFor();
  await plan.getByLabel('Subject', { exact: true }).selectOption({ label: 'Mathematics' });
  await plan.getByLabel('Curriculum week').selectOption('10');
  await plan.getByRole('button', { name: 'Assign session', exact: true }).click();
  await plan.getByText('Session assigned. Existing learning progress is unchanged.').waitFor();
  await plan.getByLabel('Subject', { exact: true }).selectOption({ label: 'English Language' });
  await plan.getByLabel('Curriculum week').selectOption('unknown');
  await plan.getByLabel('Unit', { exact: true }).selectOption({ label: 'Synthetic QA unit' });
  await plan.getByRole('button', { name: 'Assign session', exact: true }).click();
  await plan.getByRole('button', { name: 'Save plan', exact: true }).nth(1).waitFor();
  const assignment = plan.locator('article').filter({ has: page.getByRole('button', { name: 'Save plan', exact: true }) }).first();
  await assignment.getByLabel('Priority (0 first)').fill('2');
  await assignment.getByLabel('Date', { exact: true }).fill('2099-01-01');
  await Promise.all([
    page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().includes('/assignments/') && r.status() === 200),
    assignment.getByRole('button', { name: 'Save plan', exact: true }).click(),
  ]);
  const future = plan.locator('article').filter({ hasText: '2099-01-01' });
  await Promise.all([
    page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().includes('/assignments/') && r.status() === 200),
    future.getByRole('button', { name: 'Cancel assignment', exact: true }).click(),
  ]);
  await future.waitFor({ state: 'detached' });
  // Reassign both canonical fixture sessions after cancellation/rescheduling.
  for (const subject of ['Mathematics', 'English Language']) {
    await plan.getByLabel('Subject', { exact: true }).selectOption({ label: subject });
    await plan.getByRole('button', { name: 'Assign session', exact: true }).click();
    await plan.getByText('Session assigned. Existing learning progress is unchanged.').waitFor();
  }
  await page.screenshot({ path: path.join(artifacts, 'parent-desktop.png') });
  await fits();
  for (const width of [320, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await fits();
    if (width === 375) {
      await plan.getByLabel('Curriculum week').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(artifacts, 'parent-mobile.png') });
    }
  }
  await page.getByRole('button', { name: /log out/i }).click();
  await login('planning-student@example.test');
  await page.waitForURL('**/student');
  const choices = page.getByRole('region', { name: 'Choose your learning', exact: true });
  await choices.getByRole('button', { name: 'Start assigned session', exact: true }).nth(1).waitFor();
  assert.equal(await choices.getByRole('button', { name: 'Start session', exact: true }).count(), 2);
  await choices.getByLabel('Subject', { exact: true }).selectOption({ label: 'English Language' });
  await choices.getByLabel('Curriculum week').selectOption('unknown');
  await choices.getByLabel('Unit', { exact: true }).selectOption({ label: 'Synthetic QA unit' });
  assert.equal(await choices.getByRole('button', { name: 'Start session', exact: true }).count(), 1);
  await choices.getByLabel('Subject', { exact: true }).selectOption('');
  for (const width of [320, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 1000 }); await fits();
    if (width === 375 || width === 1440) {
      await choices.getByLabel('Curriculum week').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(artifacts, `student-${width}.png`) });
    }
  }
  // Read-only dashboard refresh proves browsing/planning did not award completion or XP.
  const state = await page.evaluate(async () => {
    const child = JSON.parse(localStorage.getItem('activeChild'));
    const response = await fetch(`http://127.0.0.1:8012/api/student/dashboard/${child.id}`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
    return response.json();
  });
  assert.equal(state.completed_lessons_count, 0); assert.equal(state.xp, 0);
  // Open the existing lesson screen without starting voice, microphone or Realtime.
  await choices.getByRole('button', { name: 'Start assigned session', exact: true }).first().click();
  await page.waitForURL('**/lesson');
  await page.getByRole('button', { name: '🎙️ Start Class', exact: true }).first().waitFor();
  await page.goBack();
  await page.waitForURL('**/student');
  await choices.getByRole('button', { name: 'Start session', exact: true }).first().click();
  await page.waitForURL('**/lesson');
  await page.getByRole('button', { name: '🎙️ Start Class', exact: true }).first().waitFor();
  assert.equal(errors.length, 0, JSON.stringify(errors));
  assert.equal(consoleErrors.length, 0, JSON.stringify(consoleErrors));
  assert.equal(failures.length, 0, JSON.stringify(failures));
  console.log(JSON.stringify({ result: 'PASS', widths: [320,375,390,430,768,1024,1440], artifacts, pageErrors: errors, consoleErrors, failedApiRequests: failures, resourceDiagnostics }));
} catch (e) {
  await page.screenshot({ path: path.join(artifacts, 'failure.png'), fullPage: true });
  console.error(JSON.stringify({ artifacts, errors, failures }));
  throw e;
} finally { await browser.close(); }
