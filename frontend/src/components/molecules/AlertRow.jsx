import React from 'react';

export default function AlertRow({ icon, iconBg = '#FFF1F0', title, subtitle, rightElement }) {
  return (
    <div className="alert-row">
      <div className="ai" style={{ background: iconBg }}>
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div className="at">{title}</div>
        <div className="as">{subtitle}</div>
      </div>
      {rightElement && <div>{rightElement}</div>}
    </div>
  );
}
