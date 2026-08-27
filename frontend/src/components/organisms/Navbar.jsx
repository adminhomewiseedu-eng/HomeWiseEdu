import React from 'react';
import BrandLogo from '../molecules/BrandLogo';
import ChildAvatar from '../atoms/ChildAvatar';

export default function Navbar({ currentScreen, userRole, onNavigate, activeChild, currentUser, onLogout }) {
  const normalized = (currentScreen || '').replace('/', '');
  const isHidden = ['', 'landing', 'signup', 'login', 'add-child', 'addchild', 'lesson', 'quiz', 'submit', 'complete'].includes(normalized);
  if (isHidden || normalized.startsWith('admin')) return null;

  const initial = currentUser?.avatar || currentUser?.name?.[0]?.toUpperCase() || 'U';

  const handleLogoClick = () => {
    if (currentUser) {
      onNavigate(currentUser.role === 'admin' ? '/admin' : currentUser.role === 'student' ? '/student' : '/parent');
    } else {
      onNavigate('/');
    }
  };

  return (
    <div className="appbar">
      <div className="wrap">
        <BrandLogo onClick={handleLogoClick} />

        <div className="appbar-right">
          {(normalized === 'student' || normalized === 'portfolio') && userRole === 'parent' && (
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('/parent')} style={{ fontWeight: 600 }}>
              ← Parent Dashboard
            </button>
          )}

          {userRole === 'parent' && (
            <div className="plan-tag">✨ Premium</div>
          )}

          {activeChild && normalized === 'student'
            ? <ChildAvatar className="avatar-btn" childId={activeChild.id} profileImageUrl={activeChild.profile_image_url} fallback={activeChild.avatar} style={{ cursor: 'pointer' }} onClick={onLogout} title="Log out" />
            : <div className="avatar-btn" onClick={onLogout} title="Log out" style={{ cursor: 'pointer' }}>{initial}</div>}
        </div>
      </div>
    </div>
  );
}
