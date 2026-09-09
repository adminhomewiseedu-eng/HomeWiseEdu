import React, { useEffect, useState } from 'react';
import BrandLogo from '../molecules/BrandLogo';
import ChildAvatar from '../atoms/ChildAvatar';
import { Settings, LogOut } from 'lucide-react';
import { parentAPI } from '../../services/api';

export default function Navbar({ currentScreen, userRole, onNavigate, activeChild, currentUser, onLogout, parentProfileRevision = 0 }) {
  const normalized = (currentScreen || '').replace('/', '');
  const isHidden = ['', 'landing', 'signup', 'login', 'forgot-password', 'reset-password', 'add-child', 'addchild', 'lesson', 'quiz', 'submit', 'complete'].includes(normalized);
  if (isHidden || normalized.startsWith('admin')) return null;

  const initial = currentUser?.avatar || currentUser?.name?.[0]?.toUpperCase() || 'U';
  const [parentImage, setParentImage] = useState(null);
  useEffect(() => {
    let url;
    if (userRole === 'parent') parentAPI.getParentProfileImage().then(({ data }) => { url = URL.createObjectURL(data); setParentImage(url); }).catch(() => setParentImage(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [userRole, parentProfileRevision]);

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
        <button className="parent-brand" onClick={handleLogoClick}><BrandLogo variant="crest" /><span>HomeWiseEdu</span></button>

        <div className="appbar-right">
          {(normalized === 'student' || normalized === 'portfolio') && userRole === 'parent' && (
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('/parent')} style={{ fontWeight: 600 }}>
              ← Parent Dashboard
            </button>
          )}

          {userRole === 'parent' && <button className="header-icon-action" onClick={() => onNavigate('/parent/settings/profile')} title="Settings" aria-label="Settings"><Settings size={19}/></button>}

          {activeChild && normalized === 'student'
            ? <ChildAvatar className="avatar-btn" childId={activeChild.id} profileImageUrl={activeChild.profile_image_url} fallback={activeChild.avatar} style={{ cursor: 'pointer' }} onClick={onLogout} title="Log out" />
            : userRole === 'parent' ? <button className="parent-avatar-control" onClick={() => onNavigate('/parent/profile')} title="View profile" aria-label="View profile">{parentImage ? <img src={parentImage} alt="Parent profile"/> : initial}</button>
            : <div className="avatar-btn">{initial}</div>}
          <button className="header-icon-action header-logout-action" onClick={onLogout} title="Log out" aria-label="Log out"><LogOut size={19}/></button>
        </div>
      </div>
    </div>
  );
}
