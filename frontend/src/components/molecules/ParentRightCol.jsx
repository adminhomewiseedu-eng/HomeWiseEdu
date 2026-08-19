import React from 'react';
import AlertRow from './AlertRow';
import RecommendationCard from './RecommendationCard';

export default function ParentRightCol({ alerts = [], recommendations = [], recStates = {}, onRecommendationAction }) {
  return (
    <div>
      <div className="card pad" style={{ marginBottom: 20 }}>
        <div className="card-head">
          <h3>Daily Alerts</h3>
          <span className="pill" style={{ background: '#FFF1F0', color: 'var(--rose)' }}>{alerts.length}</span>
        </div>
        {alerts.map((al, idx) => (
          <AlertRow
            key={idx}
            icon={al.severity === 'high' ? '🔴' : al.severity === 'medium' ? '🟠' : '🟢'}
            iconBg={al.severity === 'high' ? '#FFF1F0' : al.severity === 'medium' ? '#FFF7ED' : '#F0FDF4'}
            title={al.title}
            subtitle={al.subtitle}
          />
        ))}
      </div>

      <div className="card pad" style={{ marginBottom: 20 }}>
        <div className="card-head"><h3>AI Recommendations</h3></div>
        {recommendations.map((rec) => (
          <RecommendationCard
            key={rec.id}
            id={rec.id}
            title={rec.title}
            description={rec.description}
            status={recStates[rec.id] || rec.status}
            onApprove={(id) => onRecommendationAction(id, 'approve')}
            onOverride={(id) => onRecommendationAction(id, 'override')}
          />
        ))}
      </div>

      <div className="card pad">
        <div className="card-head"><h3>Reports</h3></div>
        <p style={{ color: 'var(--ink-soft)', fontWeight: 600, fontSize: 14, marginBottom: 14 }}>
          Download a full progress report including skills, evidence highlights, and character notes.
        </p>
        <button className="btn btn-teal btn-sm" style={{ width: '100%' }} onClick={() => alert('PDF report downloaded!')}>
          📄 Download Report (PDF)
        </button>
      </div>
    </div>
  );
}
