import React from 'react';
import ProgressBar from '../atoms/ProgressBar';
import ChildAvatar from '../atoms/ChildAvatar';

export default function SubjectProgressRow({
  icon,
  childId,
  profileImageUrl,
  iconBg = '#DBEAFE',
  name,
  percentage = 0,
  fillBackground,
}) {
  return (
    <div className="subj-row">
      <ChildAvatar className="ico" style={{ background: iconBg }} childId={childId} profileImageUrl={profileImageUrl} fallback={icon} />
      <div className="nm">{name}</div>
      <ProgressBar percentage={percentage} fillBackground={fillBackground} />
      <div className="pc">{percentage}%</div>
    </div>
  );
}
