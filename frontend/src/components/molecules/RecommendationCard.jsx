import React from 'react';

export default function RecommendationCard({
  id,
  title,
  description,
  status = 'pending', // 'pending' | 'approved' | 'overridden'
  onApprove,
  onOverride,
}) {
  return (
    <div className="rec-card">
      <div className="rt">🤖 {title}</div>
      <div className="rd">{description}</div>
      <div className="rec-btns">
        <button
          className="rec-approve"
          onClick={() => onApprove(id)}
          style={{ opacity: status === 'approved' ? 0.6 : 1 }}
        >
          {status === 'approved' ? '✓ Approved' : 'Approve'}
        </button>
        <button
          className="rec-override"
          onClick={() => onOverride(id)}
          style={{ opacity: status === 'overridden' ? 0.6 : 1 }}
        >
          {status === 'overridden' ? 'Overridden' : 'Override'}
        </button>
      </div>
    </div>
  );
}
