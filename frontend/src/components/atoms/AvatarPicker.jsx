import React from 'react';

const DEFAULT_AVATARS = [
  { emoji: '🦁', bg: '#DBEAFE' },
  { emoji: '🐨', bg: '#FEF3C7' },
  { emoji: '🐸', bg: '#DCFCE7' },
  { emoji: '🦊', bg: '#FFE4E1' },
  { emoji: '🐰', bg: '#F3E8FF' },
];

export default function AvatarPicker({ selected, onSelect, avatars = DEFAULT_AVATARS }) {
  return (
    <div style={{ display: 'flex', gap: 9, flexWrap: 'wrap' }}>
      {avatars.map((av) => (
        <div
          key={av.emoji}
          className={`avpick ${selected === av.emoji ? 'sel' : ''}`}
          style={{ background: av.bg }}
          onClick={() => onSelect(av.emoji)}
        >
          {av.emoji}
        </div>
      ))}
    </div>
  );
}
