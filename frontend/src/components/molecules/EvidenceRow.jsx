import React from 'react';

export default function EvidenceRow({ icon = '📝', iconBg = '#DBEAFE', title, isVerified, score }) {
  return (
    <div className="ev-row">
      <div className="ai" style={{ background: iconBg }}>
        {icon}
      </div>
      <div className="et">{title}</div>
      <span
        className="status-chip"
        style={{
          background: isVerified ? '#F0FDF4' : '#FFF7ED',
          color: isVerified ? '#16A34A' : 'var(--amber)',
        }}
      >
        {isVerified ? `✅ ${score ? `Score ${score}%` : 'Verified'}` : '⚠ Needs review'}
      </span>
    </div>
  );
}
