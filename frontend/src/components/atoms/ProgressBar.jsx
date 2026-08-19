import React from 'react';

export default function ProgressBar({
  percentage = 0,
  fillBackground = 'linear-gradient(90deg, var(--teal), var(--sky))',
  height = 9,
  className = '',
  style = {},
}) {
  const boundedPct = Math.min(100, Math.max(0, percentage));
  return (
    <div className={`bar ${className}`.trim()} style={{ height, ...style }}>
      <span style={{ width: `${boundedPct}%`, background: fillBackground }} />
    </div>
  );
}
