import React from 'react';
import SubjectProgressRow from './SubjectProgressRow';
import AlertRow from './AlertRow';
import EvidenceRow from './EvidenceRow';

export default function ParentLeftCol({ childrenList = [], weeklySummary, recentEvidence = [], onViewPortfolio }) {
  return (
    <div>
      <div className="card pad" style={{ marginBottom: 20 }}>
        <div className="card-head"><h3>Overall Progress</h3></div>
        {childrenList.map((c, idx) => (
          <SubjectProgressRow
            key={c.id}
            icon={c.avatar}
            childId={c.id}
            profileImageUrl={c.profile_image_url}
            iconBg={idx % 2 === 0 ? '#DBEAFE' : '#FEF3C7'}
            name={c.name}
            percentage={c.progress_percentage}
            fillBackground={idx % 2 === 0 ? 'linear-gradient(90deg, var(--sky), var(--teal))' : 'linear-gradient(90deg, var(--leaf), var(--teal))'}
          />
        ))}
      </div>

      <div className="card pad" style={{ marginBottom: 20 }}>
        <div className="card-head"><h3>Weekly Summary</h3></div>
        <AlertRow icon="✅" iconBg="#F0FDF4" title="Strengths" subtitle={weeklySummary?.strengths} />
        <AlertRow icon="⚠️" iconBg="#FFF7ED" title="Needs improvement" subtitle={weeklySummary?.needs_improvement} />
        <AlertRow icon="✝️" iconBg="#F3E8FF" title="Bible reflection" subtitle={weeklySummary?.bible_reflection} />
      </div>

      <div className="card pad">
        <div className="card-head">
          <h3>Learning Evidence</h3>
          <a onClick={onViewPortfolio}>View all →</a>
        </div>
        {recentEvidence.map((ev, i) => (
          <EvidenceRow key={i} title={`${ev.subject} · ${ev.lesson_title}`} isVerified={ev.verified} />
        ))}
      </div>
    </div>
  );
}
