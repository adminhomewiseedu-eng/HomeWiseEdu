import React from 'react';

const STEPS = [
  { num: 1, title: 'Learn', desc: "The AI tutor teaches today's lesson, reading alongside your child." },
  { num: 2, title: 'Practise', desc: 'A quick quiz checks understanding, with instant feedback.' },
  { num: 3, title: 'Prove it', desc: 'Your child submits work that AI evaluates and verifies as evidence.' },
  { num: 4, title: 'Progress', desc: 'Progress updates, a certificate awaits, and the next lesson unlocks.' },
];

export default function LandingHowItWorks() {
  return (
    <div className="section" id="how" style={{ paddingTop: 0 }}>
      <div className="wrap">
        <div className="steps-band">
          <div className="hero-blob" style={{ width: 200, height: 200, background: 'var(--grape)', top: -40, right: 60, opacity: 0.4 }}></div>
          <div style={{ textAlign: 'center', position: 'relative', zIndex: 2, marginBottom: 36 }}>
            <span className="section-eyebrow" style={{ color: 'var(--sun)' }}>
              The daily learning flow
            </span>
            <div className="section-title" style={{ color: '#fff', marginTop: 8 }}>
              How a lesson works
            </div>
          </div>
          <div className="steps-grid">
            {STEPS.map((s) => (
              <div className="step" key={s.num}>
                <div className="num">{s.num}</div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
