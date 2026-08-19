import React from 'react';
import BrandLogo from '../molecules/BrandLogo';
import { useAdminDashboard } from '../../hooks/useAdminDashboard';

export default function AdminDashboardScreen({ onExit }) {
  const { data, loading } = useAdminDashboard();

  if (loading || !data) {
    return <div style={{ padding: 40, textAlign: 'center' }}><h2>Loading admin...</h2></div>;
  }

  const { admin_name, stats, revenue_trend = [], curriculum_engagement = [], top_students = [], recent_alerts = [] } = data;

  return (
    <div className="admin-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <BrandLogo color="#fff" style={{ marginBottom: 30, padding: '0 8px' }} />
        <div className="side-link"><span>📚</span> Curriculum</div>
        <div className="side-link"><span>🎒</span> Students</div>
        <div className="side-link on"><span>📊</span> Analytics</div>
        <div className="side-link"><span>💷</span> Earnings</div>
        <div className="side-link"><span>🗂️</span> Content</div>
        <div className="side-link"><span>⚙️</span> Settings</div>
        <div style={{ marginTop: 24 }}>
          <button className="btn btn-ghost btn-sm" style={{ color: 'rgba(255,255,255,.6)' }} onClick={onExit}>
            ← Exit admin
          </button>
        </div>
      </div>

      {/* Main Area */}
      <div className="admin-main">
        <div className="admin-topbar">
          <div style={{ fontFamily: 'Baloo 2', fontWeight: 800, fontSize: 20, color: 'var(--plum)' }}>
            Welcome, {admin_name} 👋
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <input className="admin-search" placeholder="🔍 Search students, lessons..." />
            <div className="iconbtn">🔔<span className="dot"></span></div>
            <div className="avatar-btn">J</div>
          </div>
        </div>

        <div className="admin-body">
          {/* Stats Grid */}
          <div className="stat-row-admin">
            <div className="card mini-stat"><div style={{ display: 'flex', justifyContent: 'space-between' }}><div className="mv">{stats?.total_lessons}</div><div style={{ fontSize: 20 }}>📘</div></div><div className="ml2">Total Lessons</div></div>
            <div className="card mini-stat"><div style={{ display: 'flex', justifyContent: 'space-between' }}><div className="mv">{stats?.total_evidence}</div><div style={{ fontSize: 20 }}>✅</div></div><div className="ml2">Learning Evidence</div></div>
            <div className="card mini-stat"><div style={{ display: 'flex', justifyContent: 'space-between' }}><div className="mv">{stats?.active_students}</div><div style={{ fontSize: 20 }}>🎒</div></div><div className="ml2">Active Students</div></div>
            <div className="card mini-stat"><div style={{ display: 'flex', justifyContent: 'space-between' }}><div className="mv">{stats?.monthly_revenue}</div><div style={{ fontSize: 20 }}>💷</div></div><div className="ml2">Monthly Revenue <span className="delta" style={{ color: '#16A34A' }}>+7%</span></div></div>
          </div>

          <div className="grid-3" style={{ marginBottom: 20 }}>
            {/* Revenue Trend */}
            <div className="card pad">
              <div className="card-head"><h3>Monthly Revenue</h3><span className="pill" style={{ background: '#F0FDF4', color: '#16A34A' }}>Last 6 months · +7%</span></div>
              <div style={{ fontFamily: 'Baloo 2', fontSize: 34, fontWeight: 800, color: 'var(--plum)', marginBottom: 16 }}>{stats?.monthly_revenue}</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 120 }}>
                {revenue_trend.map((r, i) => (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, height: '100%', justifyContent: 'flex-end' }}>
                    <div style={{ width: '100%', height: `${r.pct}%`, background: i < 2 ? 'linear-gradient(180deg,var(--leaf),var(--teal))' : i < 4 ? 'linear-gradient(180deg,var(--sky),var(--blue))' : 'linear-gradient(180deg,var(--grape),var(--plum))', borderRadius: '8px 8px 0 0' }} />
                    <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--ink-soft)' }}>{r.month}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Engagement Pie */}
            <div className="card pad">
              <div className="card-head"><h3>Curriculum Engagement</h3></div>
              <div className="pie" style={{ background: 'conic-gradient(var(--blue) 0 29%,var(--leaf) 29% 52%,var(--amber) 52% 75%,var(--grape) 75% 100%)', marginBottom: 18 }} />
              {curriculum_engagement.map((c, i) => (
                <div key={i} className="leg"><div className="sw" style={{ background: c.color }} /> {c.subject} <span style={{ marginLeft: 'auto', fontWeight: 800 }}>{c.pct}%</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
