import React from 'react';

export default function BrandLogo({ color = 'var(--plum)', onClick, style = {} }) {
  return (
    <div
      className="logo"
      style={{ color, cursor: onClick ? 'pointer' : 'default', ...style }}
      onClick={onClick}
    >
      <div className="logo-mark">🎓</div>
      <span>HomeWiseEdu</span>
    </div>
  );
}
