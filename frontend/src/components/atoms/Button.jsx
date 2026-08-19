import React from 'react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'grape' | 'teal' | 'ghost' | 'white'
  size = 'md', // 'sm' | 'md'
  className = '',
  style = {},
  onClick,
  disabled = false,
  type = 'button',
  ...props
}) {
  const sizeClass = size === 'sm' ? 'btn-sm' : '';
  const variantClass = `btn-${variant}`;

  return (
    <button
      type={type}
      className={`btn ${variantClass} ${sizeClass} ${className}`.trim()}
      style={style}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
