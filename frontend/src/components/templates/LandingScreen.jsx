import React from 'react';
import LandingHero from '../organisms/LandingHero';
import LandingFeatures from '../organisms/LandingFeatures';
import LandingHowItWorks from '../organisms/LandingHowItWorks';
import LandingPricing from '../organisms/LandingPricing';
import LandingCTA from '../organisms/LandingCTA';
import LandingFooter from '../organisms/LandingFooter';
import BrandLogo from '../molecules/BrandLogo';

export default function LandingScreen({ onNavigate, onStartLesson }) {
  const scrollToId = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="screen active" id="landing">
      {/* Topnav */}
      <div className="topnav">
        <div className="wrap">
          <BrandLogo />
          <div className="navlinks">
            <a onClick={() => scrollToId('features')}>Features</a>
            <a onClick={() => scrollToId('how')}>How it works</a>
            <a onClick={() => scrollToId('pricing')}>Pricing</a>
            <a onClick={() => onNavigate('login')}>Log in</a>
            <button className="btn btn-primary btn-sm" onClick={() => onNavigate('signup')}>
              Get started
            </button>
          </div>
        </div>
      </div>

      <LandingHero
        onSignup={() => onNavigate('signup')}
        onSeeLesson={onStartLesson}
      />
      <LandingFeatures />
      <LandingHowItWorks />
      <LandingPricing onSelectPlan={() => onNavigate('signup')} />
      <LandingCTA onAction={() => onNavigate('signup')} />
      <LandingFooter />
    </div>
  );
}
