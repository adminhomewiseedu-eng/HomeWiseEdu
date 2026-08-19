import React from 'react';
import BrandLogo from '../molecules/BrandLogo';

export default function AuthVisualSide({
  background = 'linear-gradient(150deg, var(--grape), var(--plum-deep))',
  title = 'Structured learning, built around your family.',
  subtitle = 'Set up in minutes. Add each child, and their curriculum is ready the same day.',
  footerText = 'Trusted by homeschooling families',
  blobBg1 = 'var(--sun)',
  blobBg2 = 'var(--coral)',
  onLogoClick,
}) {
  return (
    <div className="auth-visual" style={{ background }}>
      <div className="blob" style={{ width: 300, height: 300, background: blobBg1, top: -60, right: -60 }} />
      <div className="blob" style={{ width: 200, height: 200, background: blobBg2, bottom: 40, left: -40 }} />
      <BrandLogo color="#fff" onClick={onLogoClick} style={{ position: 'relative', zIndex: 2 }} />
      <div style={{ position: 'relative', zIndex: 2 }}>
        <h1 style={{ fontSize: 36, lineHeight: 1.15, marginBottom: 14 }}>{title}</h1>
        <p style={{ fontSize: 16, fontWeight: 600, opacity: 0.85, lineHeight: 1.6 }}>{subtitle}</p>
      </div>
      <div style={{ position: 'relative', zIndex: 2, fontWeight: 700, opacity: 0.85 }}>
        {footerText}
      </div>
    </div>
  );
}
