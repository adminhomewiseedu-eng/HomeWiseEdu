import React from 'react';
import BrandLogo from '../molecules/BrandLogo';

export default function Navbar({ currentScreen, userRole, onNavigate, activeChild, currentUser, onLogout }) {
  const normalized = (currentScreen || '').replace('/', '');
  const isHidden = ['', 'landing', 'signup', 'login', 'add-child', 'addchild', 'lesson', 'quiz', 'submit', 'complete'].includes(normalized);
  if (isHidden) return null;

  const initial = currentUser?.avatar || currentUser?.name?.[0]?.toUpperCase() || 'U';

  const handleLogoClick = () => {
    if (currentUser) {
      onNavigate(currentUser.role === 'admin' ? '/admin' : '/parent');
    } else {
      onNavigate('/');
    }
  };

  return (
    <div className="appbar">
      <div className="wrap">
        <BrandLogo onClick={handleLogoClick} />

        <div className="appbar-right">
          {(normalized === 'student' || normalized === 'portfolio' || userRole === 'student') && (
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('/parent')} style={{ fontWeight: 600 }}>
              ← Parent Dashboard
            </button>
          )}

          <div className="iconbtn">🔔<span className="dot"></span></div>

          {userRole === 'parent' && (
            <>
              <div className="iconbtn">✉️</div>
              <div className="plan-tag">✨ Premium</div>
            </>
          )}

          <div className="avatar-btn" onClick={onLogout} title="Log out" style={{ cursor: 'pointer' }}>
            {activeChild && normalized === 'student' ? activeChild.avatar : initial}
          </div>
        </div>
      </div>
    </div>
  );
}
