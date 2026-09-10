import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const dashboard=fs.readFileSync(new URL('../components/templates/AdminDashboardScreen.jsx',import.meta.url),'utf8');
const views=fs.readFileSync(new URL('../components/templates/AdminSettingsViews.jsx',import.meta.url),'utf8');
const app=fs.readFileSync(new URL('../App.jsx',import.meta.url),'utf8');

test('platform, profile and security routes remain separate',()=>{assert.match(dashboard,/SettingsNav section="platform"/);assert.match(dashboard,/base==='profile'/);assert.match(dashboard,/detailId==='profile'/);assert.match(dashboard,/detailId==='security'/)});
test('administrator dropdown exposes profile, settings and logout',()=>{assert.match(dashboard,/View Profile/);assert.match(dashboard,/> Settings</);assert.match(dashboard,/> Logout</)});
test('profile form keeps email read-only and synchronizes saved identity',()=>{assert.match(views,/value=\{form\.email\} readOnly/);assert.match(views,/await onSaved\(res\.data\)/);assert.match(app,/onProfileUpdated=/)});
test('security form contains password checks and visibility control',()=>{assert.match(views,/Current password/);assert.match(views,/Confirm new password/);assert.match(views,/New password must be different/);assert.match(views,/Show passwords/)});
