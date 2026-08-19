import React from 'react';

export default function FeatureCard({ icon, bg = '#F3E8FF', title, description }) {
  return (
    <div className="card fcard">
      <div className="fi" style={{ background: bg }}>
        {icon}
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
