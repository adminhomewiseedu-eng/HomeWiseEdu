import React from 'react';

export default function BrandLogo({ color = 'var(--plum)', onClick, style = {} }) {
  return (
    <div
      className="logo"
      style={{ color, cursor: onClick ? 'pointer' : 'default', ...style }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (event) => {
        if (event.key === 'Enter' || event.key === ' ') onClick();
      } : undefined}
      aria-label={onClick ? 'HomeWiseEdu home' : undefined}
    >
      <img
        className="brand-logo-image"
        src="/assets/homewiseedu-logo.jpg"
        alt="HomeWiseEdu — Family Under the Word"
      />
    </div>
  );
}
