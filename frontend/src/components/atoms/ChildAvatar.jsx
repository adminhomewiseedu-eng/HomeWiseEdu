import React, { useEffect, useState } from 'react';
import { parentAPI } from '../../services/api';

export default function ChildAvatar({ childId, profileImageUrl, fallback = '🦁', className = '', style = {}, onClick, title }) {
  const [imageUrl, setImageUrl] = useState(null);

  useEffect(() => {
    let active = true;
    let objectUrl = null;
    if (!childId || !profileImageUrl) {
      setImageUrl(null);
      return () => {};
    }
    parentAPI.getProfileImage(childId).then((response) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(response.data);
      setImageUrl(objectUrl);
    }).catch(() => {
      if (active) setImageUrl(null);
    });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [childId, profileImageUrl]);

  return (
    <div className={className} style={{ overflow: 'hidden', ...style }} onClick={onClick} title={title}>
      {imageUrl
        ? <img src={imageUrl} alt="Student profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        : fallback}
    </div>
  );
}
