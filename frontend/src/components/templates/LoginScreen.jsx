import React, { useState } from 'react';
import AuthVisualSide from '../organisms/AuthVisualSide';
import InputField from '../atoms/InputField';
import Button from '../atoms/Button';
import BrandLogo from '../molecules/BrandLogo';

export default function LoginScreen({ onNavigate, onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    setError('');
    try {
      await onLogin(email, password);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="screen active" id="login">
      <div className="auth-wrap">
        <AuthVisualSide
          background="linear-gradient(150deg, var(--teal), var(--plum))"
          title="Welcome back."
          subtitle=""
          footerText=""
          blobBg1="var(--sky)"
          blobBg2="transparent"
        />

        <div className="auth-form-side">
          <div className="auth-card">
            <div className="auth-form-logo"><BrandLogo onClick={() => onNavigate('/')} /></div>
            <h2>Log in</h2>
            <p className="sub">Enter your credentials to continue.</p>

            {error && (
              <div style={{ background: '#FFF1F0', color: '#DC2626', padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 700, marginBottom: 14 }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <InputField label="Email address" type="email" placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <InputField label="Password" type="password" placeholder="Your password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <Button type="submit" variant="primary" style={{ width: '100%' }} disabled={loading}>
                {loading ? 'Logging in...' : 'Log in →'}
              </Button>
            </form>

            <div className="auth-alt">
              New here? <a onClick={() => onNavigate('/signup')}>Create an account</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
