import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import AuthVisualSide from '../organisms/AuthVisualSide';
import BrandLogo from '../molecules/BrandLogo';
import Button from '../atoms/Button';
import { authAPI } from '../../services/api';

export default function ResetPasswordScreen({ onNavigate }) {
  const location = useLocation();
  const token = new URLSearchParams(location.search).get('token') || '';
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(token ? '' : 'This password reset link is invalid or has expired.');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault(); setError('');
    if (password.length < 8) return setError('Password must be at least 8 characters.');
    if (password !== confirmation) return setError('Passwords do not match.');
    setLoading(true);
    try {
      await authAPI.resetPassword(token, password);
      setSuccess(true);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'This password reset link is invalid or has expired.');
    } finally { setLoading(false); }
  };

  return <div className="screen active">
    <div className="auth-wrap">
      <AuthVisualSide title="Choose a new password." subtitle="Secure your HomeWiseEdu account with a new password." footerText="support@homewiseedu.com" centerContent />
      <div className="auth-form-side"><div className="auth-card">
        <div className="auth-form-logo"><BrandLogo onClick={() => onNavigate('/')} /></div>
        <h2>Reset password</h2>
        {success ? <>
          <div className="auth-success" role="status">Your password has been reset successfully.</div>
          <Button variant="primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => onNavigate('/login')}>Back to login</Button>
        </> : <form onSubmit={submit}>
          <p className="sub">Use at least 8 characters.</p>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <div className="field"><label>New password</label><div className="password-input-wrap"><input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} required disabled={!token} /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button></div></div>
          <div className="field"><label>Confirm new password</label><input type={showPassword ? 'text' : 'password'} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required disabled={!token} /></div>
          <Button type="submit" variant="primary" style={{ width: '100%' }} disabled={loading || !token}>{loading ? 'Resetting...' : 'Reset password'}</Button>
        </form>}
        {!success && <div className="auth-alt"><a onClick={() => onNavigate('/forgot-password')}>Request a new reset link</a></div>}
      </div></div>
    </div>
  </div>;
}
