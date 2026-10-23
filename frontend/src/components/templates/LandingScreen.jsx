import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import LandingHero from '../organisms/LandingHero';
import LandingFeatures from '../organisms/LandingFeatures';
import LandingHowItWorks from '../organisms/LandingHowItWorks';
import LandingPricing from '../organisms/LandingPricing';
import LandingCTA from '../organisms/LandingCTA';
import LandingFooter from '../organisms/LandingFooter';
import BrandLogo from '../molecules/BrandLogo';

export default function LandingScreen({ onNavigate, onStartLesson }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef(null);
  const pendingMenuActionRef = useRef(null);

  const scrollToId = (id) => {
    const el = document.getElementById(id);
    if (el) {
      const header = document.querySelector('.topnav');
      const headerHeight = header?.getBoundingClientRect().height || 0;
      el.style.scrollMarginBlockStart = `${headerHeight}px`;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      el.focus({ preventScroll: true });
    }
  };

  const scrollToProgrammes = () => scrollToId('programmes');
  const closeMenuAndRun = (action) => {
    pendingMenuActionRef.current = action;
    setMenuOpen(false);
  };

  useLayoutEffect(() => {
    if (!menuOpen && pendingMenuActionRef.current) {
      const action = pendingMenuActionRef.current;
      pendingMenuActionRef.current = null;
      action();
    }
  }, [menuOpen]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && menuOpen) {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    const handleResize = () => {
      if (window.innerWidth > 960) setMenuOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, [menuOpen]);

  return (
    <div className="screen active" id="landing">
      {/* Topnav */}
      <div className="topnav">
        <div className="wrap">
          <BrandLogo variant="crest" />
          <div className="navlinks landing-nav-desktop">
            <button className="landing-nav-link" onClick={() => scrollToId('features')}>Features</button>
            <button className="landing-nav-link" onClick={() => scrollToId('how')}>How it works</button>
            <button className="landing-nav-link" onClick={() => scrollToId('pricing')}>Pricing</button>
            <button className="landing-nav-link" onClick={() => onNavigate('/login')}>Log in</button>
            <button className="btn btn-primary btn-sm" onClick={scrollToProgrammes}>
              Get started
            </button>
          </div>
          <div className="landing-nav-compact">
            <button className="btn btn-primary btn-sm landing-compact-cta" onClick={scrollToProgrammes}>Get started</button>
            <button
              ref={menuButtonRef}
              type="button"
              className="landing-menu-toggle"
              aria-expanded={menuOpen}
              aria-controls="landing-mobile-menu"
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
            </button>
          </div>
          <nav id="landing-mobile-menu" className="landing-mobile-menu" aria-label="Landing page" hidden={!menuOpen}>
            <button className="landing-mobile-link" onClick={() => closeMenuAndRun(() => scrollToId('features'))}>Features</button>
            <button className="landing-mobile-link" onClick={() => closeMenuAndRun(() => scrollToId('how'))}>How it works</button>
            <button className="landing-mobile-link" onClick={() => closeMenuAndRun(() => scrollToId('pricing'))}>Pricing</button>
            <button className="landing-mobile-link landing-mobile-login" onClick={() => closeMenuAndRun(() => onNavigate('/login'))}>Log in</button>
            <button className="btn btn-primary" onClick={() => closeMenuAndRun(scrollToProgrammes)}>Get started</button>
          </nav>
        </div>
      </div>

      <LandingHero
        onSignup={scrollToProgrammes}
        onSeeLesson={onStartLesson}
      />
      <section id="programmes" className="programme-choice" aria-labelledby="programme-choice-title" tabIndex="-1">
        <div className="wrap">
          <h2 id="programme-choice-title" className="section-title">Choose your learning pathway</h2>
          <p className="section-sub">Start the full homeschool experience, or join our focused Bible Study programme.</p>
          <div className="programme-choice-grid">
            <article className="programme-choice-card">
              <span className="programme-choice-icon">🏡</span><h3>Full Homeschool</h3>
              <p>A complete family learning experience across your selected academic subjects.</p>
              <button className="btn btn-primary" onClick={() => onNavigate('/signup')}>Choose Full Homeschool</button>
            </article>
            <article className="programme-choice-card bible">
              <span className="programme-choice-badge">Free during testing</span>
              <span className="programme-choice-icon">📖</span><h3>Bible Study</h3>
              <p>A dedicated Understanding The Word journey for parents and children.</p>
              <button className="btn btn-teal" onClick={() => onNavigate('/bible-study/signup')}>Choose Bible Study</button>
            </article>
          </div>
        </div>
      </section>
      <LandingFeatures />
      <LandingHowItWorks />
      <LandingPricing onSelectPlan={() => onNavigate('signup')} />
      <LandingCTA onAction={scrollToProgrammes} />
      <LandingFooter />
    </div>
  );
}
