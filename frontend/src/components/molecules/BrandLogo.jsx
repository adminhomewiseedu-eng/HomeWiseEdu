import React from 'react';

export default function BrandLogo({ color = 'var(--plum)', onClick, style = {}, variant = 'full' }) {
  const isAdaptive = variant === 'adaptive';
  const imageSrc = variant === 'crest' ? '/assets/homewiseedu-crest.png' : '/assets/homewiseedu-logo-full.png';

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
      {isAdaptive ? (
        <>
          <img className="brand-logo-image brand-logo-full" src="/assets/homewiseedu-logo-full.png" alt="HomeWiseEdu — Family Under the Word" />
          <img className="brand-logo-image brand-logo-crest" src="/assets/homewiseedu-crest.png" alt="" aria-hidden="true" />
        </>
      ) : (
        <img
          className={`brand-logo-image brand-logo-${variant}`}
          src={imageSrc}
          alt={variant === 'crest' ? 'HomeWiseEdu' : 'HomeWiseEdu — Family Under the Word'}
        />
      )}
    </div>
  );
}
