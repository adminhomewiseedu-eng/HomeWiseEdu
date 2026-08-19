import React from 'react';
import ProgressBar from '../atoms/ProgressBar';

export default function KidCard({
  name,
  grade,
  age,
  avatar = '🦁',
  avatarBg = '#DBEAFE',
  progressPercentage = 50,
  progressGradient = 'linear-gradient(90deg, var(--teal), var(--sky))',
  statusBadge = 'Doing great!',
  statusBadgeType = 'success', // 'success' | 'warning'
  xp = 0,
  lessonsCount = 0,
  certsCount = 0,
  onClick,
}) {
  return (
    <div className="card kid-card" onClick={onClick}>
      <div className="kid-top">
        <div className="kid-av" style={{ background: avatarBg }}>
          {avatar}
        </div>
        <div>
          <h3>{name}</h3>
          <div className="grade">{grade} · Age {age}</div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 800, color: 'var(--ink-soft)', marginBottom: 6 }}>
        <span>Overall progress</span>
        <span>{progressPercentage}%</span>
      </div>

      <ProgressBar percentage={progressPercentage} fillBackground={progressGradient} />

      <div style={{ marginTop: 12 }}>
        <span
          className="pill"
          style={{
            background: statusBadgeType === 'warning' ? '#FFF1F0' : '#F0FDF4',
            color: statusBadgeType === 'warning' ? 'var(--rose)' : '#16A34A',
          }}
        >
          {statusBadgeType === 'warning' ? `⚠ ${statusBadge}` : `✅ ${statusBadge}`}
        </span>
      </div>

      <div className="kid-stats">
        <div className="kid-stat">
          <div className="v">{xp}</div>
          <div className="l">XP</div>
        </div>
        <div className="kid-stat">
          <div className="v">{lessonsCount}</div>
          <div className="l">Lessons</div>
        </div>
        <div className="kid-stat">
          <div className="v">{certsCount}</div>
          <div className="l">Certs</div>
        </div>
      </div>
    </div>
  );
}
