import React from 'react';

export default function EvidenceForm({
  taskDescription = 'Draw or explain two fractions that are equivalent to ¾, and show your working.',
  textContent,
  onTextChange,
  fileName,
  onFileSelect,
  onSubmit,
  isSubmitting = false,
}) {
  return (
    <div className="submit-area card pad" style={{ width: '100%' }}>
      <div className="card-head">
        <h3>📤 Submit your learning evidence</h3>
      </div>
      <p style={{ color: 'var(--ink-soft)', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>
        Show what you learned! Write your answer or upload a photo of your work. Ms Ade will check it and add it to your portfolio.
      </p>

      <div style={{ background: 'var(--cream)', borderRadius: 14, padding: 14, margin: '14px 0' }}>
        <div style={{ fontWeight: 800, color: 'var(--plum)', fontSize: 14, marginBottom: 4 }}>
          ✍️ Your task
        </div>
        <div style={{ fontSize: 14, color: 'var(--ink)', fontWeight: 600 }}>
          {taskDescription}
        </div>
      </div>

      <textarea
        rows={4}
        value={textContent}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="Type your answer here..."
        style={{
          width: '100%',
          padding: 13,
          border: '2px solid var(--line)',
          borderRadius: 13,
          fontFamily: 'inherit',
          fontWeight: 600,
          fontSize: 14,
          resize: 'vertical',
        }}
      />

      <label className="upload-zone" style={{ display: 'block' }}>
        <input
          type="file"
          onChange={onFileSelect}
          style={{ display: 'none' }}
          accept="image/*,.pdf,video/*"
        />
        {fileName ? `📎 Attached: ${fileName}` : '📎 Tap to upload a photo or file'}
        <div style={{ fontSize: 12, color: 'var(--ink-soft)', fontWeight: 600, marginTop: 4 }}>
          JPG, PNG, PDF, or video
        </div>
      </label>

      <button
        className="btn btn-primary"
        style={{ width: '100%' }}
        onClick={onSubmit}
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Evaluating with Ms Ade…' : 'Submit to Ms Ade →'}
      </button>
    </div>
  );
}
