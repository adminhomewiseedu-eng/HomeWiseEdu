import React from 'react';

export default function RoleSwitcher({ currentRole, onSelectRole }) {
  const roles = [
    { key: 'parent', label: '👪 Parent' },
    { key: 'student', label: '🎒 Student' },
    { key: 'admin', label: '⚙️ Admin' },
  ];

  return (
    <div className="role-switch" id="roleSwitch">
      {roles.map((r) => (
        <button
          key={r.key}
          className={currentRole === r.key ? 'on' : ''}
          onClick={() => onSelectRole(r.key)}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
