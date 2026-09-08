import React, { useState } from 'react';
import AuthVisualSide from '../organisms/AuthVisualSide';
import BrandLogo from '../molecules/BrandLogo';
import InputField from '../atoms/InputField';
import Button from '../atoms/Button';
import { authAPI } from '../../services/api';

export default function ForgotPasswordScreen({ onNavigate }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true); setError(''); setMessage('');
    try {
      const response = await authAPI.forgotPassword(email);
      setMessage(response.data.message);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Password reset is temporarily unavailable. Please try again later.');
    } finally { setLoading(false); }
  };

  return <div className="screen active">
    <div className="auth-wrap">
      <AuthVisualSide title="Reset your password." subtitle="We'll help you securely return to your HomeWiseEdu account." footerText="homewiseedu.com" centerContent />
      <div className="auth-form-side"><div className="auth-card">
        <div className="auth-form-logo"><BrandLogo onClick={() => onNavigate('/')} /></div>
        <h2>Forgot password?</h2>
        <p className="sub">Enter your account email address.</p>
        {message ? <div className="auth-success" role="status">{message}</div> : <form onSubmit={submit}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <InputField label="Email address" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <Button type="submit" variant="primary" style={{ width: '100%' }} disabled={loading}>{loading ? 'Sending...' : 'Send reset link'}</Button>
        </form>}
        <div className="auth-alt"><a onClick={() => onNavigate('/login')}>← Back to login</a></div>
      </div></div>
    </div>
  </div>;
}
