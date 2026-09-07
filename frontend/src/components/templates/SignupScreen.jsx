import React, { useState } from 'react';
import AuthVisualSide from '../organisms/AuthVisualSide';
import InputField from '../atoms/InputField';
import Button from '../atoms/Button';
import BrandLogo from '../molecules/BrandLogo';

export default function SignupScreen({ onNavigate, onSignup }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) return;
    setLoading(true);
    setError('');
    try {
      await onSignup(name, email, password);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="screen active" id="signup">
      <div className="auth-wrap">
        <AuthVisualSide />

        <div className="auth-form-side">
          <div className="auth-card">
            <div className="auth-form-logo"><BrandLogo onClick={() => onNavigate('/')} /></div>
            <h2>Create your account</h2>
            <p className="sub">Start your family's learning journey.</p>

            {error && (
              <div style={{ background: '#FFF1F0', color: '#DC2626', padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 700, marginBottom: 14 }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <InputField label="Your name" placeholder="e.g. Sarah Wilson" value={name} onChange={(e) => setName(e.target.value)} required />
              <InputField label="Email address" type="email" placeholder="e.g. you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <InputField label="Password" type="password" placeholder="Create a password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <Button type="submit" variant="primary" style={{ width: '100%' }} disabled={loading}>
                {loading ? 'Creating account...' : 'Create account →'}
              </Button>
            </form>

            <div className="auth-alt">
              Already have an account? <a onClick={() => onNavigate('/login')}>Log in</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
