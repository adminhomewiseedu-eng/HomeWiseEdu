import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const page = fs.readFileSync(new URL('../components/templates/ParentSettingsScreen.jsx', import.meta.url), 'utf8');
const overview = fs.readFileSync(new URL('../components/templates/ParentProfileScreen.jsx', import.meta.url), 'utf8');
const nav = fs.readFileSync(new URL('../components/organisms/Navbar.jsx', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../App.jsx', import.meta.url), 'utf8');

test('parent profile renders settings sections and read-only email', () => {
  assert.match(page, /Parent Profile/); assert.match(page, /Account/); assert.match(page, /Security/);
  assert.match(page, /readOnly/); assert.match(page, /Save Changes/);
});

test('settings sidebar switches between separate routed views', () => {
  assert.match(page, /section==='profile'/); assert.match(page, /section==='account'/); assert.match(page, /section==='security'/);
  assert.match(page, /\/parent\/settings\/account/); assert.match(page, /\/parent\/settings\/security/);
});

test('profile supports image preview and validation feedback', () => {
  assert.match(page, /URL\.createObjectURL/); assert.match(page, /image\/jpeg/); assert.match(page, /5\s*\*\s*1024\s*\*\s*1024/);
  assert.match(page, /profile-message/);
});

test('parent header exposes settings, profile avatar, and logout', () => {
  assert.match(nav, /HomeWiseEdu/); assert.match(nav, /Settings/); assert.match(nav, /View profile/); assert.match(nav, /Log out/);
  assert.match(nav, /\/parent\/profile/); assert.match(nav, /parentProfileRevision/);
  assert.match(nav, /header-icon-action/); assert.doesNotMatch(nav, /<span>Settings<\/span>/); assert.doesNotMatch(nav, /<span>Log out<\/span>/);
});

test('parent profile overview is read-only and links to editing in settings', () => {
  assert.match(app, /path="\/parent\/profile"/);
  assert.match(overview, /My Profile/); assert.match(overview, /Phone number/); assert.match(overview, /Address/);
  assert.match(overview, /Role/); assert.match(overview, /Joined/); assert.match(overview, /Edit profile/);
  assert.match(overview, /\/parent\/settings\/profile/);
  assert.doesNotMatch(overview, /<form/); assert.doesNotMatch(overview, /Save Changes/);
});

test('saving a profile refreshes shared parent identity and avatar state', () => {
  assert.match(page, /onProfileUpdated\?\.\(updated\)/);
  assert.match(app, /setParentProfileRevision/); assert.match(app, /setCurrentUser/);
});
