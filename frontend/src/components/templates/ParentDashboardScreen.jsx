import React, { useState } from 'react';
import KidCard from '../molecules/KidCard';
import ParentLeftCol from '../molecules/ParentLeftCol';
import ParentRightCol from '../molecules/ParentRightCol';
import { useParentDashboard } from '../../hooks/useParentDashboard';
import EditChildModal from '../organisms/EditChildModal';

const CHILD_COLORS = [
  { bg: '#DBEAFE', gradient: 'linear-gradient(90deg, var(--teal), var(--sky))' },
  { bg: '#FEF3C7', gradient: 'linear-gradient(90deg, var(--leaf), var(--teal))' },
  { bg: '#F3E8FF', gradient: 'linear-gradient(90deg, var(--grape), var(--plum))' },
  { bg: '#DCFCE7', gradient: 'linear-gradient(90deg, var(--leaf), var(--sky))' },
];

export default function ParentDashboardScreen({ parentId, onSelectChild, onAddChild, onViewPortfolio }) {
  const { data, loading, error, recStates, handleRecommendation, refetch } = useParentDashboard(parentId);
  const [editingChild, setEditingChild] = useState(null);

  if (loading) {
    return <div className="wrap pad" style={{ textAlign: 'center', padding: '100px 0' }}><h2>Loading dashboard...</h2></div>;
  }

  if (error || !data) {
    return (
      <div className="wrap pad" style={{ textAlign: 'center', padding: '80px 0' }}>
        <h2>Could not load dashboard</h2>
        <p style={{ color: 'var(--ink-soft)', margin: '10px 0 20px' }}>{error || 'Please check your connection'}</p>
        <button className="btn btn-primary btn-sm" onClick={refetch}>Try again</button>
      </div>
    );
  }

  const { parent_name, children = [], weekly_summary, alerts = [], recommendations = [], recent_evidence = [] } = data;

  return (
    <div className="wrap">
      <div className="page-head">
        <h1>Welcome, {parent_name} 👋</h1>
        <p>{children.length ? "Manage your children's learning." : "Add your first child to get started."}</p>
      </div>

      <div style={{ margin: '20px 0' }}>
        <div className="kids-grid">
          {children.map((c, idx) => {
            const colors = CHILD_COLORS[idx % CHILD_COLORS.length];
            return (
              <KidCard
                key={c.id}
                name={c.name}
                grade={c.grade}
                age={c.age}
                avatar={c.avatar}
                childId={c.id}
                profileImageUrl={c.profile_image_url}
                avatarBg={colors.bg}
                progressPercentage={c.progress_percentage}
                progressGradient={colors.gradient}
                statusBadge={c.status_badge}
                statusBadgeType={c.status_badge === 'Doing great!' ? 'success' : c.status_badge === 'Needs attention' ? 'warning' : 'info'}
                xp={c.xp}
                lessonsCount={c.completed_lessons}
                certsCount={c.certificates_count}
                onClick={() => onSelectChild(c)}
                onEdit={() => setEditingChild(c)}
              />
            );
          })}

          <div className="add-kid" onClick={onAddChild}>
            <div className="plus">+</div>
            <h3 style={{ color: 'var(--plum)', fontSize: 18 }}>Add a child</h3>
            <p style={{ color: 'var(--ink-soft)', fontWeight: 600, marginTop: 3, fontSize: 14 }}>Set up their curriculum</p>
          </div>
        </div>
      </div>

      {children.length > 0 && (
        <div className="grid-3" style={{ marginBottom: 56 }}>
          <ParentLeftCol childrenList={children} weeklySummary={weekly_summary} recentEvidence={recent_evidence} onViewPortfolio={onViewPortfolio} />
          <ParentRightCol alerts={alerts} recommendations={recommendations} recStates={recStates} onRecommendationAction={handleRecommendation} />
        </div>
      )}
      {editingChild && <EditChildModal child={editingChild} onClose={() => setEditingChild(null)} onSaved={refetch} />}
    </div>
  );
}
