import React, { useEffect, useState } from 'react';
import { CalendarDays, Mail, MapPin, Pencil, Phone, ShieldCheck, UserRound } from 'lucide-react';
import { parentAPI } from '../../services/api';

const EMPTY = { first_name:'', last_name:'', email:'', phone_number:'', address_line_1:'', address_line_2:'', city:'', state_region:'', postal_code:'', country:'', role:'', joined_at:'' };

export default function ParentProfileScreen({ onNavigate, profileRevision = 0 }) {
  const [profile, setProfile] = useState(EMPTY);
  const [imageUrl, setImageUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let objectUrl = '';
    setLoading(true);
    Promise.all([parentAPI.getProfile(), parentAPI.getParentProfileImage().catch(() => null)])
      .then(([profileResponse, imageResponse]) => {
        setProfile({ ...EMPTY, ...profileResponse.data });
        if (imageResponse) {
          objectUrl = URL.createObjectURL(imageResponse.data);
          setImageUrl(objectUrl);
        } else setImageUrl('');
      })
      .catch((err) => setError(err.response?.data?.detail || 'Could not load your profile.'))
      .finally(() => setLoading(false));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [profileRevision]);

  if (loading) return <main className="parent-settings-page"><div className="settings-card">Loading your profile…</div></main>;
  if (error) return <main className="parent-settings-page"><div className="settings-card"><div className="profile-message error">{error}</div></div></main>;

  const fullName = [profile.first_name, profile.last_name].filter(Boolean).join(' ') || 'Parent';
  const initials = `${profile.first_name?.[0] || ''}${profile.last_name?.[0] || ''}` || 'P';
  const address = [profile.address_line_1, profile.address_line_2, profile.city, profile.state_region, profile.postal_code, profile.country].filter(Boolean);

  return <main className="parent-settings-page">
    <div className="settings-heading"><button onClick={() => onNavigate('/parent')}>← Back</button><div><h1>My Profile</h1><p>View your parent account information.</p></div></div>
    <section className="settings-card parent-profile-overview">
      <div className="profile-overview-hero">
        <div className="parent-profile-preview large">{imageUrl ? <img src={imageUrl} alt={fullName}/> : initials}</div>
        <div className="profile-overview-name"><span className="profile-role"><ShieldCheck size={15}/>{profile.role || 'Parent'}</span><h2>{fullName}</h2><p>{profile.email || 'No email supplied'}</p></div>
        <button className="btn btn-primary btn-sm profile-edit-button" onClick={() => onNavigate('/parent/settings/profile')}><Pencil size={16}/> Edit profile</button>
      </div>
      <div className="profile-overview-grid">
        <div className="profile-detail"><Mail/><div><span>Email</span><strong>{profile.email || 'Not provided'}</strong></div></div>
        <div className="profile-detail"><Phone/><div><span>Phone number</span><strong>{profile.phone_number || 'Not provided'}</strong></div></div>
        <div className="profile-detail wide"><MapPin/><div><span>Address</span><strong>{address.length ? address.join(', ') : 'Not provided'}</strong></div></div>
        <div className="profile-detail"><UserRound/><div><span>Role</span><strong>{profile.role || 'Parent'}</strong></div></div>
        <div className="profile-detail"><CalendarDays/><div><span>Joined</span><strong>{profile.joined_at ? new Date(profile.joined_at).toLocaleDateString() : '—'}</strong></div></div>
      </div>
    </section>
  </main>;
}
