import React, { useState } from 'react';
import InputField from '../atoms/InputField';
import AvatarPicker from '../atoms/AvatarPicker';
import ChildAvatar from '../atoms/ChildAvatar';
import { parentAPI } from '../../services/api';

export default function EditChildModal({ child, onClose, onSaved }) {
  const [name, setName] = useState(child.name || '');
  const [age, setAge] = useState(child.age || 9);
  const [avatar, setAvatar] = useState(child.avatar || '🦁');
  const [email, setEmail] = useState(child.student_email || '');
  const [password, setPassword] = useState('');
  const [image, setImage] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (password && password.length < 8) return setError('The new password must be at least 8 characters.');
    if (image && image.size > 5 * 1024 * 1024) return setError('Profile picture must be 5 MB or smaller.');
    setLoading(true);
    try {
      await parentAPI.updateChild(child.id, { name: name.trim(), age: Number(age), avatar });
      if (email.trim() || password) {
        await parentAPI.updateStudentCredentials(child.id, { email: email.trim() || null, password: password || null });
      }
      if (removeImage) await parentAPI.removeProfileImage(child.id);
      if (image) await parentAPI.uploadProfileImage(child.id, image);
      await onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'The student profile could not be updated.');
    } finally {
      setLoading(false);
    }
  };

  return <div className="admin-modal-backdrop" onClick={onClose}>
    <div className="card pad admin-modal" onClick={(event) => event.stopPropagation()}>
      <button className="admin-modal-close" onClick={onClose}>✕</button>
      <h2 style={{ color: 'var(--plum)', marginBottom: 12 }}>Edit {child.name}</h2>
      <ChildAvatar className="kid-av" childId={child.id} profileImageUrl={child.profile_image_url} fallback={avatar} style={{ background: '#DBEAFE', marginBottom: 16 }} />
      {error && <div style={{ background: '#FFF1F0', color: '#DC2626', padding: 10, borderRadius: 10, marginBottom: 12 }}>{error}</div>}
      <form onSubmit={submit}>
        <InputField label="Student name" value={name} onChange={(e) => setName(e.target.value)} required />
        <InputField label="Age" type="number" value={age} onChange={(e) => setAge(e.target.value)} required />
        <div className="field"><label>Fallback avatar</label><AvatarPicker selected={avatar} onSelect={setAvatar} /></div>
        <div className="field"><label>New profile picture</label><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImage(e.target.files?.[0] || null)} /></div>
        {child.profile_image_url && <label style={{ display: 'flex', gap: 8, marginBottom: 16 }}><input type="checkbox" checked={removeImage} onChange={(e) => setRemoveImage(e.target.checked)} /> Remove current profile picture</label>}
        <h3 style={{ color: 'var(--plum)', margin: '16px 0 8px' }}>Student login</h3>
        <InputField label="Student email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Optional until login is enabled" />
        <InputField label={child.student_email ? 'New password (leave blank to keep current)' : 'Password required to enable login'} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <p style={{ fontSize: 12, color: 'var(--ink-soft)', margin: '-8px 0 16px' }}>Stored passwords are never displayed.</p>
        <button className="btn btn-primary" type="submit" disabled={loading}>{loading ? 'Saving…' : 'Save student profile'}</button>
      </form>
    </div>
  </div>;
}
