import React from 'react';
import ProgressBar from '../atoms/ProgressBar';
import ChildAvatar from '../atoms/ChildAvatar';

export default function KidCard({
  name,
  grade,
  age,
  avatar = '🦁',
  childId,
  profileImageUrl,
  avatarBg = '#DBEAFE',
  progressPercentage = 50,
  progressGradient = 'linear-gradient(90deg, var(--teal), var(--sky))',
  statusBadge = 'Doing great!',
  statusBadgeType = 'success', // 'success' | 'warning'
  xp = 0,
  lessonsCount = 0,
  certsCount = 0,
  onClick,
  onEdit,
}) {
  return (
    <div className="card kid-card" onClick={onClick}>
      {onEdit && <button className="btn btn-ghost btn-sm" style={{ float: 'right', padding: '5px 9px' }} onClick={(event) => { event.stopPropagation(); onEdit(); }}>Edit</button>}
      <div className="kid-top">
        <ChildAvatar className="kid-av" style={{ background: avatarBg }} childId={childId} profileImageUrl={profileImageUrl} fallback={avatar} />
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
