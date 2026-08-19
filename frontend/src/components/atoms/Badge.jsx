import React from 'react';

export default function Badge({
  children,
  bg = '#F3E8FF',
  color = 'var(--grape)',
  className = '',
  style = {},
}) {
  return (
    <span
      className={`pill ${className}`.trim()}
      style={{ background: bg, color, ...style }}
    >
      {children}
    </span>
  );
}
