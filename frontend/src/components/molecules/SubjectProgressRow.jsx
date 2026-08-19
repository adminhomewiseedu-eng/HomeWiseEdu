import React from 'react';
import ProgressBar from '../atoms/ProgressBar';

export default function SubjectProgressRow({
  icon,
  iconBg = '#DBEAFE',
  name,
  percentage = 0,
  fillBackground,
}) {
  return (
    <div className="subj-row">
      <div className="ico" style={{ background: iconBg }}>
        {icon}
      </div>
      <div className="nm">{name}</div>
      <ProgressBar percentage={percentage} fillBackground={fillBackground} />
      <div className="pc">{percentage}%</div>
    </div>
  );
}
