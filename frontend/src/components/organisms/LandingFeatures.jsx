import React from 'react';
import FeatureCard from '../molecules/FeatureCard';

const FEATURES = [
  { icon: '📚', bg: '#F3E8FF', title: 'Structured curriculum', description: 'A fixed, proven sequence of subjects, units and lessons — so nothing is skipped and every child progresses in order.' },
  { icon: '🗣️', bg: '#FEF3C7', title: 'AI teaching & feedback', description: 'A patient AI tutor explains each lesson aloud, evaluates written work, and gives instant, encouraging feedback.' },
  { icon: '✅', bg: '#DCFCE7', title: 'Learning evidence', description: 'Proof of real learning — not just ticks. Children submit work that\'s evaluated, verified, and saved to their portfolio.' },
  { icon: '📊', bg: '#DBEAFE', title: 'Parent visibility', description: 'Alerts, weekly summaries, and AI recommendations you can approve or override — full clarity, always.' },
  { icon: '🎨', bg: '#FFE4E1', title: 'Real-world skills', description: 'Life skills, media & communication, and character woven through — preparing children for the real world.' },
  { icon: '✝️', bg: '#CCFBF1', title: 'Character & faith', description: 'Bible and character are core, integrated into every lesson and every report — growing wisdom, not just knowledge.' },
];

export default function LandingFeatures() {
  return (
    <div className="section" id="features">
      <div className="wrap">
        <div style={{ textAlign: 'center' }}>
          <span className="section-eyebrow">More than a learning app</span>
        </div>
        <div className="section-title" style={{ marginTop: 10 }}>
          A complete education system
        </div>
        <div className="section-sub">
          Six systems working together to give your children real, structured, provable learning.
        </div>
        <div className="feature-grid">
          {FEATURES.map((f, i) => (
            <FeatureCard key={i} {...f} />
          ))}
        </div>
      </div>
    </div>
  );
}
