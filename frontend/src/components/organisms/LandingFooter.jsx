import React from 'react';
import BrandLogo from '../molecules/BrandLogo';

export default function LandingFooter() {
  return (
    <footer>
      <div className="wrap">
        <BrandLogo color="#fff" />
        <div style={{ fontWeight: 600 }}>
          © 2026 HomeWiseEdu · Structured first, AI-enhanced second
        </div>
      </div>
    </footer>
  );
}
