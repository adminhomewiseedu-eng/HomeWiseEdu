import React from 'react';

export default function InputField({
  label,
  type = 'text',
  value,
  onChange,
  placeholder = '',
  required = false,
  ...props
}) {
  return (
    <div className="field">
      {label && <label>{label}</label>}
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        {...props}
      />
    </div>
  );
}
