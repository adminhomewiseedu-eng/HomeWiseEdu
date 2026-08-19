import React from 'react';
import Button from '../atoms/Button';

export default function PricingCard({
  planName,
  currency,
  price,
  period = '/mo',
  subtitle,
  features = [],
  isFeatured = false,
  badgeText = 'Most popular',
  onSelect,
}) {
  return (
    <div className={`card price-card ${isFeatured ? 'feat' : ''}`}>
      {isFeatured && <div className="badge-pop">{badgeText}</div>}
      <div className="plan">{planName}</div>
      <div className="amt">
        <span className="cur">{currency}</span>
        <span className="p1">{price}</span>
        <span>{period}</span>
      </div>
      <p style={{ color: 'var(--ink-soft)', fontWeight: 600, fontSize: 14 }}>
        {subtitle}
      </p>
      <ul>
        {features.map((feat, idx) => (
          <li key={idx} style={{ opacity: feat.included ? 1 : 0.4 }}>
            {feat.included ? '✅' : '✖'} {feat.text}
          </li>
        ))}
      </ul>
      <Button
        variant={isFeatured ? 'grape' : 'ghost'}
        style={{ width: '100%', border: isFeatured ? 'none' : '2px solid var(--line)' }}
        onClick={onSelect}
      >
        Start trial
      </Button>
    </div>
  );
}
