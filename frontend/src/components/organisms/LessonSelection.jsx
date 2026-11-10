import React, { useEffect, useState } from 'react';
import { learningPlanAPI } from '../../services/api';
import { filterSessions, weekLabel, localDate, prioritizedAssignments } from '../../utils/lessonSelection';

function AssignmentEditor({ item, childId, refresh, report }) {
  const [date, setDate] = useState(item.scheduled_date);
  const [priority, setPriority] = useState(item.priority);
  const [busy, setBusy] = useState(false);
  const update = async payload => {
    setBusy(true);
    try { await learningPlanAPI.update(childId, item.assignment_id, payload); await refresh(); }
    catch (e) { report(e.response?.data?.detail || 'Could not update assignment.'); }
    finally { setBusy(false); }
  };
  return <div className="lesson-plan-actions">
    <label>Date<input type="date" value={date} required onChange={e => setDate(e.target.value)} /></label>
    <label>Priority (0 first)<input type="number" min="0" step="1" value={priority} onChange={e => setPriority(e.target.value)} /></label>
    <button className="btn btn-grape btn-sm" disabled={busy || item.available === false || !date || priority === '' || Number(priority) < 0} onClick={() => update({ scheduled_date: date, priority: Number(priority) })}>Save plan</button>
    <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => update({ cancelled: true })}>Cancel assignment</button>
  </div>;
}

export default function LessonSelection({ childId, planning = false, onStartLesson }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [subject, setSubject] = useState('');
  const [week, setWeek] = useState('');
  const [unit, setUnit] = useState('');
  const [date, setDate] = useState(localDate);
  const [priority, setPriority] = useState(0);
  const [busy, setBusy] = useState(false);
  const load = async () => {
    const response = await learningPlanAPI.browse(childId);
    setData(response.data);
  };
  useEffect(() => {
    let active = true;
    setData(null); setError(''); setSubject(''); setWeek(''); setUnit('');
    learningPlanAPI.browse(childId).then(r => { if (active) setData(r.data); })
      .catch(e => { if (active) setError(e.response?.data?.detail || 'Could not load learning choices.'); });
    return () => { active = false; };
  }, [childId]);
  const assign = async session => {
    setBusy(true); setError(''); setNotice('');
    try {
      await learningPlanAPI.assign(childId, { lesson_id: session.lesson_id, day_number: session.day_number, scheduled_date: date, priority: Number(priority) });
      await load(); setNotice('Session assigned. Existing learning progress is unchanged.');
    } catch (e) { setError(e.response?.data?.detail || 'Could not assign session.'); }
    finally { setBusy(false); }
  };
  const sessions = data?.sessions || [];
  const subjects = [...new Map(sessions.map(s => [s.subject_id, s.subject])).entries()];
  const weeks = [...new Set(sessions.filter(s => !subject || String(s.subject_id) === subject).map(s => s.curriculum_week))]
    .filter(w => w != null).sort((a, b) => a - b);
  const assignments = prioritizedAssignments(data?.assignments || []);
  const units = [...new Map(filterSessions(sessions, subject, week).map(s => [s.unit_id, s.unit])).entries()];
  const visible = filterSessions(sessions, subject, week, unit);
  return <section className="card pad lesson-plan" aria-label={planning ? 'Plan learning' : 'Choose your learning'}>
    <h3>{planning ? 'Plan learning' : 'Assigned by your parent'}</h3>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!data && !error && <p role="status">Loading learning choices…</p>}
    {assignments.length ? <div className="lesson-plan-list">{assignments.map(item => <article className="lesson-plan-item" key={item.assignment_id}>
      <strong>{item.subject} · {item.title}</strong>
      <p>{weekLabel(item.curriculum_week)} · Day {item.day_number} {item.activity_type} · {item.scheduled_date} · Priority {item.priority}</p>
      {item.available === false && <p>This session is no longer eligible. Cancel it and choose an available session.</p>}
      {planning ? <AssignmentEditor item={item} childId={childId} refresh={load} report={setError} /> :
        <button className="btn btn-primary btn-sm" disabled={item.available === false} onClick={() => onStartLesson(item)}>{item.status === 'in_progress' ? 'Resume' : 'Start'} assigned session</button>}
    </article>)}</div> : data && <p>No outstanding assignments. {planning ? 'Choose sessions below.' : 'You can choose a published lesson below.'}</p>}
    {planning && data?.assignments?.some(a => a.status === 'completed') && <details><summary>Completed assignments</summary>
      {data.assignments.filter(a => a.status === 'completed').map(a => <p key={a.assignment_id}>{a.subject} · {a.title} · Day {a.day_number} · Completed</p>)}
    </details>}
    <h3>{planning ? 'Browse curriculum' : 'Browse your subjects'}</h3>
    <p>Choose any available session at your level. Choosing a later week does not complete earlier work.</p>
    <div className="lesson-plan-filters">
      <label>Subject<select aria-label="Subject" value={subject} onChange={e => { setSubject(e.target.value); setWeek(''); setUnit(''); }}><option value="">All enrolled subjects</option>{subjects.map(([id, title]) => <option key={id} value={id}>{title}</option>)}</select></label>
      <label>Curriculum week<select aria-label="Curriculum week" value={week} onChange={e => { setWeek(e.target.value); setUnit(''); }}><option value="">All available weeks</option>{weeks.map(w => <option key={w} value={w}>Week {w}</option>)}<option value="unknown">Week not supplied</option></select></label>
      <label>Unit<select aria-label="Unit" value={unit} onChange={e => setUnit(e.target.value)}><option value="">All available units</option>{units.map(([id, title]) => <option key={id} value={id}>{title}</option>)}</select></label>
      {planning && <><label>Assignment date<input type="date" required value={date} onChange={e => setDate(e.target.value)} /></label>
        <label>Priority (0 first)<input type="number" min="0" step="1" value={priority} onChange={e => setPriority(e.target.value)} /></label></>}
    </div>
    {sessions.some(s => s.curriculum_week == null) && <p className="lesson-plan-hint">Some curriculum has no authored week number. Find it by subject, unit and lesson; lesson numbers are not week numbers.</p>}
    {data && !visible.length && <p>No published sessions match these choices.</p>}
    <div className="lesson-plan-list">{visible.map(item => <article className="lesson-plan-item" key={`${item.lesson_id}:${item.day_number}`}>
      <strong>{item.subject} · {item.title}</strong>
      <p>{item.unit} · {weekLabel(item.curriculum_week)} · Day {item.day_number} {item.activity_type} · {item.status.replace('_', ' ')}</p>
      {planning ? <button className="btn btn-grape btn-sm" disabled={busy || !date || priority === '' || Number(priority) < 0} onClick={() => assign(item)}>Assign session</button> :
        <button className="btn btn-grape btn-sm" onClick={() => onStartLesson(item)}>{item.status === 'completed' ? 'Review' : item.status === 'in_progress' ? 'Resume' : 'Start'} session</button>}
    </article>)}</div>
  </section>;
}
