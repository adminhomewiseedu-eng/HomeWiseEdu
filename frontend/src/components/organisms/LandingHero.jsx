import React from 'react';
import Button from '../atoms/Button';
import Badge from '../atoms/Badge';

export default function LandingHero({ onSignup, onSeeLesson }) {
  return (
    <div className="hero">
      <div className="wrap">
        <div className="hero-blob" style={{ width: 340, height: 340, background: 'var(--sun)', top: -60, right: -40 }}></div>
        <div className="hero-blob" style={{ width: 260, height: 260, background: 'var(--teal)', bottom: -80, left: -60 }}></div>
        <div className="hero-grid">
          <div>
            <Badge bg="#F3E8FF" color="var(--grape)">
              ✨ Structured curriculum first, AI second
            </Badge>
            <h1 style={{ marginTop: 16 }}>
              Homeschooling with <span className="hl">structure & confidence</span>
            </h1>
            <p className="lead">
              A complete, AI-supported curriculum that teaches your children, proves real learning, and gives you full visibility — academically, personally, and spiritually.
            </p>
            <div className="hero-cta">
              <Button variant="primary" onClick={onSignup}>
                Start free trial →
              </Button>
              <Button variant="ghost" onClick={onSeeLesson}>
                ▶ See a lesson
              </Button>
            </div>
            <div className="trust">
              <div className="t"><div className="dot" style={{ background: '#F3E8FF' }}>📚</div> Full curriculum</div>
              <div className="t"><div className="dot" style={{ background: '#DCFCE7' }}>✅</div> Proof of learning</div>
              <div className="t"><div className="dot" style={{ background: '#FEF3C7' }}>✝️</div> Character & Bible</div>
            </div>
          </div>

          <div style={{ position: 'relative' }}>
            <div className="floaty" style={{ background: 'var(--sun)', color: 'var(--plum-deep)', top: -14, left: -12 }}>
              ⭐ +35 XP
            </div>
            <div className="floaty" style={{ background: 'var(--teal)', color: '#fff', bottom: 16, right: -14, animationDelay: '1.5s' }}>
              ✅ Evidence verified
            </div>
            <div className="hero-card">
              <div className="ml">
                <div className="tr">
                  <div className="av">👩🏾‍🏫</div>
                  <div style={{ fontWeight: 800, fontSize: 14 }}>Ms Ade is teaching…</div>
                </div>
                <div className="bub">
                  Great thinking, James! So if we start with the units column, what's 3 + 4? Take your time 😊
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
