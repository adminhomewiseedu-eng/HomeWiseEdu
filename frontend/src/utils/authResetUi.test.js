import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const app = readFileSync(new URL('../App.jsx', import.meta.url), 'utf8');
const login = readFileSync(new URL('../components/templates/LoginScreen.jsx', import.meta.url), 'utf8');
const forgot = readFileSync(new URL('../components/templates/ForgotPasswordScreen.jsx', import.meta.url), 'utf8');
const reset = readFileSync(new URL('../components/templates/ResetPasswordScreen.jsx', import.meta.url), 'utf8');

test('login exposes the forgot-password route and both reset routes are public', () => {
  assert.match(login, /Forgot password\?/);
  assert.match(app, /path="\/forgot-password"/);
  assert.match(app, /path="\/reset-password"/);
  assert.match(app, /'forgot-password', 'reset-password'/);
});

test('forgot-password form submits and presents the privacy-safe server response', () => {
  assert.match(forgot, /authAPI\.forgotPassword\(email\)/);
  assert.match(forgot, /setMessage\(response\.data\.message\)/);
  assert.match(forgot, /Send reset link/);
});

test('reset page validates matching secure passwords and handles success and invalid links', () => {
  assert.match(reset, /password\.length < 8/);
  assert.match(reset, /password !== confirmation/);
  assert.match(reset, /Your password has been reset successfully\./);
  assert.match(reset, /This password reset link is invalid or has expired\./);
  assert.match(reset, /Request a new reset link/);
});
