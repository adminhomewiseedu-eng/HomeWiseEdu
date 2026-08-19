import React from 'react';
import Button from '../atoms/Button';

export default function LandingCTA({ onAction }) {
  return (
    <div className="section">
      <div className="wrap">
        <div className="cta-band">
          <span className="section-eyebrow" style={{ color: '#fff', opacity: 0.8 }}>
            Ready when you are
          </span>
          <h2>Give your children structure today</h2>
          <p>Join families making learning at home calm, consistent, and provable.</p>
          <Button variant="white" onClick={onAction}>
            Create your free account →
          </Button>
        </div>
      </div>
    </div>
  );
}
