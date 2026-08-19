import React, { useState } from 'react';
import PricingCard from '../molecules/PricingCard';

const PRICES = {
  '£': [9, 19, 34],
  '$': [12, 24, 42],
  '€': [10, 21, 38],
  'A$': [17, 34, 59],
};

export default function LandingPricing({ onSelectPlan }) {
  const [currency, setCurrency] = useState('£');
  const priceList = PRICES[currency] || PRICES['£'];

  return (
    <div className="section" id="pricing" style={{ paddingTop: 0 }}>
      <div className="wrap">
        <div style={{ textAlign: 'center' }}>
          <span className="section-eyebrow">Simple, fair pricing</span>
        </div>
        <div className="section-title" style={{ marginTop: 10 }}>
          Choose your family's plan
        </div>
        <div className="section-sub">
          Every plan includes a free trial. Cancel anytime.
        </div>

        <div className="currency-tabs">
          {['£', '$', '€', 'A$'].map((sym) => (
            <button
              key={sym}
              className={currency === sym ? 'on' : ''}
              onClick={() => setCurrency(sym)}
            >
              {sym === '£' ? '🇬🇧 GBP' : sym === '$' ? '🇺🇸 USD' : sym === '€' ? '🇪🇺 EUR' : '🇦🇺 AUD'}
            </button>
          ))}
        </div>

        <div className="pricing-grid">
          <PricingCard
            planName="Basic"
            currency={currency}
            price={priceList[0]}
            subtitle="For one child getting started."
            features={[
              { text: '1 child', included: true },
              { text: 'Full curriculum access', included: true },
              { text: 'AI tutor & feedback', included: true },
              { text: 'Progress tracking', included: true },
              { text: 'Learning evidence', included: false },
              { text: 'Certificates', included: false },
            ]}
            onSelect={onSelectPlan}
          />

          <PricingCard
            planName="Premium"
            currency={currency}
            price={priceList[1]}
            subtitle="For growing families."
            isFeatured={true}
            features={[
              { text: 'Up to 3 children', included: true },
              { text: 'Everything in Basic', included: true },
              { text: 'Learning evidence system', included: true },
              { text: 'Portfolio & certificates', included: true },
              { text: 'Weekly parent reports', included: true },
              { text: 'AI recommendations', included: true },
            ]}
            onSelect={onSelectPlan}
          />

          <PricingCard
            planName="Elite"
            currency={currency}
            price={priceList[2]}
            subtitle="For the full experience."
            features={[
              { text: 'Unlimited children', included: true },
              { text: 'Everything in Premium', included: true },
              { text: 'Media & life-skills subjects', included: true },
              { text: 'Term & annual PDF reports', included: true },
              { text: 'Priority AI evaluation', included: true },
              { text: 'Early access to new subjects', included: true },
            ]}
            onSelect={onSelectPlan}
          />
        </div>
      </div>
    </div>
  );
}
