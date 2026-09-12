import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, BarChart3, BookOpen, Bot, ChevronLeft, FileBarChart, FileCheck2, FolderOpen,
  GraduationCap, LayoutDashboard, Mail, Menu, MoreVertical, Pencil, Plus, Search, Settings,
  UserCheck, UserRound, Users, UserX, WalletCards, X } from 'lucide-react';
import BrandLogo from '../molecules/BrandLogo';
import { AdminProfileForm, AdminProfileOverview, AdminSecurity, SettingsNav } from './AdminSettingsViews';
import { adminAPI, curriculumAPI, evidenceAPI, reportsAPI } from '../../services/api';
import { parentPageCount } from '../../utils/adminParentsUi';

const NAV = [
  ['Overview', '/admin', LayoutDashboard], ['Curriculum', '/admin/curriculum', BookOpen],
  ['Parents', '/admin/parents', UserRound], ['Students', '/admin/students', Users], ['Learning Evidence', '/admin/evidence', FileCheck2],
  ['Analytics', '/admin/analytics', BarChart3], ['Reports', '/admin/reports', FileBarChart],
  ['Earnings / Subscriptions', '/admin/earnings', WalletCards], ['Content', '/admin/content', FolderOpen],
  ['AI Monitoring', '/admin/ai-monitoring', Bot], ['Settings', '/admin/settings', Settings],
];

const Empty = ({ children }) => <div className="admin-empty">{children}</div>;
const Loading = () => <div className="admin-empty">Loading…</div>;
const ErrorState = ({ message, retry }) => <div className="admin-empty admin-error"><strong>Something went wrong.</strong><div>{message}</div>{retry && <button className="btn btn-ghost btn-sm" onClick={retry}>Try again</button>}</div>;
const Status = ({ value }) => <span className={`admin-status ${String(value).toLowerCase().replace('_', '-')}`}>{String(value).replace('_', ' ')}</span>;
const formatDate = (value) => value ? new Date(value).toLocaleDateString() : 'No activity yet';

function useAdminData(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const load = async () => {
    setState((old) => ({ ...old, loading: true, error: '' }));
    try { const response = await loader(); setState({ data: response.data, loading: false, error: '' }); }
    catch (error) { setState({ data: null, loading: false, error: error.response?.data?.detail || error.message }); }
  };
  useEffect(() => { load(); }, deps);
  return { ...state, reload: load };
}

function StatCard({ label, value, icon: Icon }) {
  return <div className="card mini-stat"><div className="admin-stat-top"><div className="mv">{value ?? 'Not configured'}</div><Icon size={20} /></div><div className="ml2">{label}</div></div>;
}

function Overview() {
  const state = useAdminData(adminAPI.getDashboard, []);
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorState message={state.error} retry={state.reload} />;
  const stats = state.data.stats;
  return <>
    <div className="admin-stat-grid">
      <StatCard label="Total Students" value={stats.total_students} icon={Users} />
      <StatCard label="Active Students (30 days)" value={stats.active_students} icon={Activity} />
      <StatCard label="Parents" value={stats.parents} icon={Users} />
      <StatCard label="Total Lessons" value={stats.total_lessons} icon={BookOpen} />
      <StatCard label="Published Lessons" value={stats.published_lessons} icon={BookOpen} />
      <StatCard label="Pending Curriculum Days" value={stats.pending_curriculum_items} icon={FolderOpen} />
      <StatCard label="Learning Evidence" value={stats.total_evidence} icon={FileCheck2} />
      <StatCard label="AI Tutor Sessions" value={stats.ai_tutor_sessions} icon={Bot} />
    </div>
    <div className="admin-grid-2">
      <section className="card pad"><h3>Certificates</h3><div className="admin-big-number">{stats.certificates_issued}</div><p>No certificate persistence exists yet.</p></section>
      <section className="card pad"><h3>Subscriptions and revenue</h3><Empty>{state.data.billing.message}</Empty></section>
    </div>
  </>;
}

function Curriculum() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null); const [message, setMessage] = useState('');
  const [validation, setValidation] = useState(null); const [busy, setBusy] = useState(false);
  const [filters, setFilters] = useState({ search: '', level: '', subject: '', status: '', country: '' });
  const state = useAdminData(curriculumAPI.getAdminLessons, []);
  const filtered = useMemo(() => (state.data || []).filter((lesson) =>
    (!filters.search || `${lesson.title} ${lesson.subtopic} ${lesson.unit}`.toLowerCase().includes(filters.search.toLowerCase())) &&
    (!filters.level || String(lesson.level) === filters.level) && (!filters.subject || lesson.subject === filters.subject) &&
    (!filters.status || lesson.status === filters.status) && (!filters.country || lesson.curriculum_country === filters.country)), [state.data, filters]);
  const submitFile = async (mode) => {
    if (!file) return; setBusy(true); setMessage('');
    const body = new FormData(); body.append('file', file);
    try {
      const response = await (mode === 'validate' ? curriculumAPI.validateCSV(body) : curriculumAPI.importCSV(body));
      setValidation(response.data.stats); setMessage(response.data.message);
      if (mode === 'import') await state.reload();
    } catch (error) { setValidation(null); setMessage(error.response?.data?.detail || 'CSV operation failed.'); }
    finally { setBusy(false); }
  };
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorState message={state.error} retry={state.reload} />;
  const subjects = [...new Set(state.data.map((item) => item.subject))];
  return <>
    <section className="card pad admin-import">
      <h3>Import curriculum blueprint</h3><p>Validate first, then import. New lesson days remain pending until explicitly published.</p>
      <div className="admin-actions"><input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] || null); setValidation(null); }} />
        <button className="btn btn-ghost btn-sm" disabled={!file || busy} onClick={() => submitFile('validate')}>Validate CSV</button>
        <button className="btn btn-primary btn-sm" disabled={!file || busy || !validation} onClick={() => submitFile('import')}>Import as pending</button></div>
      {message && <div role="status" className="admin-notice">{message}</div>}
      {validation && <><div className="admin-summary">{Object.entries(validation).filter(([,value])=>!Array.isArray(value)).map(([key, value]) => <span key={key}><strong>{value}</strong> {key.replaceAll('_', ' ')}</span>)}</div>{validation.hierarchy_identity_changes?.length>0&&<div className="admin-notice"><strong>Hierarchy additions requiring review</strong><ul>{validation.hierarchy_identity_changes.map((item,index)=><li key={`${item.type}-${index}`}>{item.type.replaceAll('_',' ')}: {item.value||`Lesson ${item.lesson_number}`} {item.subject?`· ${item.subject}`:''} {item.unit?`· ${item.unit}`:''}</li>)}</ul></div>}</>}
    </section>
    <section className="card pad">
      <div className="admin-section-title"><div><h3>Curriculum hierarchy</h3><p>Level → Subject → Unit → Lesson → Lesson Day</p></div><strong>{filtered.length} lessons</strong></div>
      <div className="admin-filters"><input placeholder="Search lessons, units, topics…" value={filters.search} onChange={(e) => setFilters({...filters, search:e.target.value})} />
        <select value={filters.level} onChange={(e) => setFilters({...filters, level:e.target.value})}><option value="">All levels</option>{Array.from({length:14},(_,i)=><option key={i}>{i}</option>)}</select>
        <select value={filters.subject} onChange={(e) => setFilters({...filters, subject:e.target.value})}><option value="">All subjects</option>{subjects.map(x=><option key={x}>{x}</option>)}</select>
        <select value={filters.status} onChange={(e) => setFilters({...filters, status:e.target.value})}><option value="">All statuses</option><option>pending</option><option>published</option><option>archived</option></select>
        <select value={filters.country} onChange={(e) => setFilters({...filters, country:e.target.value})}><option value="">All education systems</option>{[...new Set(state.data.map(x=>x.curriculum_country).filter(Boolean))].map(x=><option key={x}>{x}</option>)}</select></div>
      {!filtered.length ? <Empty>All imported lessons have been reviewed, or no curriculum matches these filters.</Empty> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Lesson</th><th>Level</th><th>Subject / Unit</th><th>Days</th><th>Status</th><th></th></tr></thead><tbody>{filtered.map((lesson)=><tr key={lesson.id}><td><strong>{lesson.lesson_number}. {lesson.title}</strong><small>{lesson.subtopic}</small>{lesson.quiz_review_required&&<small>Quiz review required</small>}</td><td>{lesson.level}</td><td>{lesson.subject}<small>{lesson.unit}</small></td><td>{lesson.days}/3</td><td><Status value={lesson.status}/></td><td><button className="btn btn-ghost btn-sm" onClick={()=>navigate(`/admin/curriculum/${lesson.id}`)}>Review</button></td></tr>)}</tbody></table></div>}
    </section>
  </>;
}

function LessonDayEditor({ day, onSaved }) {
  const [editing,setEditing]=useState(false); const [busy,setBusy]=useState(false);
  const [form,setForm]=useState({key_concept:day.key_concept||'',ai_script:day.ai_script||'',real_world_context:day.real_world_context||'',visual_support:day.visual_support||''});
  const save=async()=>{setBusy(true);try{await curriculumAPI.updateLessonDay(day.id,form);setEditing(false);await onSaved();}finally{setBusy(false)}};
  if(!editing)return <button className="btn btn-ghost btn-sm" onClick={()=>setEditing(true)}>Edit day</button>;
  return <div className="admin-edit-form"><label>Key concept<textarea value={form.key_concept} onChange={e=>setForm({...form,key_concept:e.target.value})}/></label><label>Teaching script<textarea value={form.ai_script} onChange={e=>setForm({...form,ai_script:e.target.value})}/></label><label>Real-world context<textarea value={form.real_world_context} onChange={e=>setForm({...form,real_world_context:e.target.value})}/></label><label>Visual guidance<textarea value={form.visual_support} onChange={e=>setForm({...form,visual_support:e.target.value})}/></label><div className="admin-actions"><button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>Save</button><button className="btn btn-ghost btn-sm" onClick={()=>setEditing(false)}>Cancel</button></div></div>;
}

function CurriculumDetail({ lessonId }) {
  const navigate = useNavigate(); const state = useAdminData(() => curriculumAPI.getLessonDetail(lessonId), [lessonId]);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(''); const [deleteInfo,setDeleteInfo]=useState(null);
  if (state.loading) return <Loading />; if (state.error) return <ErrorState message={state.error} retry={state.reload}/>;
  const lesson = state.data; const published = lesson.days.length === 3 && lesson.days.every(d => ['active','published'].includes(String(d.status).toLowerCase()));
  const toggle = async () => { setBusy(true); try { await curriculumAPI.setLessonPublication(lesson.id, !published); await state.reload(); setMessage(!published?'Lesson published.':'Lesson returned to pending.'); } catch(e){setMessage(e.response?.data?.detail||'Update failed.');} finally{setBusy(false);} };
  const toggleArchive = async () => { setBusy(true); try { await curriculumAPI.setLessonArchive(lesson.id,!lesson.archived); await state.reload(); setMessage(lesson.archived?'Lesson restored with its previous publication state.':'Lesson archived. Student history was preserved.'); } catch(e){setMessage(e.response?.data?.detail||'Update failed.');} finally{setBusy(false);} };
  const inspectDelete = async () => { setBusy(true); try { const response=await curriculumAPI.getLessonDependencies(lesson.id); setDeleteInfo(response.data); } catch(e){setMessage(e.response?.data?.detail||'Dependency check failed.');} finally{setBusy(false);} };
  const markQuizReviewed = async () => { setBusy(true); try { await curriculumAPI.setLessonQuizReview(lesson.id,false); await state.reload(); setMessage('Quiz alignment review recorded.'); } catch(e){setMessage(e.response?.data?.detail||'Update failed.');} finally{setBusy(false);} };
  const deletePermanent = async () => { if(!deleteInfo?.can_delete||!window.confirm(`Permanently delete ${lesson.title}? This cannot be undone.`))return; setBusy(true); try{await curriculumAPI.deleteLesson(lesson.id);navigate('/admin/curriculum');}catch(e){setMessage(e.response?.data?.detail?.message||e.response?.data?.detail||'Delete failed.');setDeleteInfo(e.response?.data?.detail||deleteInfo);}finally{setBusy(false);} };
  return <><button className="admin-back" onClick={()=>navigate('/admin/curriculum')}><ChevronLeft size={18}/> Back to Curriculum</button>
    <section className="card pad"><div className="admin-section-title"><div><h3>{lesson.title}</h3><p>Level {lesson.level} · {lesson.topic}</p>{lesson.quiz_review_required&&<div className="admin-notice">Curriculum changed. Review the approved quiz for alignment. <button className="btn btn-ghost btn-sm" disabled={busy} onClick={markQuizReviewed}>Mark quiz reviewed</button></div>}</div><div className="admin-actions"><button className="btn btn-ghost btn-sm" onClick={()=>window.print()}>Preview</button><button className="btn btn-primary btn-sm" disabled={busy||lesson.archived} onClick={toggle}>{published?'Unpublish':'Publish'}</button><button className="btn btn-ghost btn-sm" disabled={busy} onClick={toggleArchive}>{lesson.archived?'Restore':'Archive'}</button><button className="btn btn-ghost btn-sm" disabled={busy} onClick={inspectDelete}>Delete Permanently</button></div></div>{message&&<div className="admin-notice">{message}</div>}
      {deleteInfo&&<div className="admin-notice"><strong>{deleteInfo.can_delete?'No student history is attached.':'Permanent deletion is blocked.'}</strong>{!deleteInfo.can_delete&&<><p>This lesson has student history and must be archived instead.</p><ul>{Object.entries(deleteInfo.dependencies||{}).filter(([,count])=>count>0).map(([name,count])=><li key={name}>{name.replaceAll('_',' ')}: {count}</li>)}</ul></>}<div className="admin-actions">{deleteInfo.can_delete&&<button className="btn btn-primary btn-sm" disabled={busy} onClick={deletePermanent}>Confirm Permanent Delete</button>}{!deleteInfo.can_delete&&!lesson.archived&&<button className="btn btn-ghost btn-sm" disabled={busy} onClick={toggleArchive}>Archive instead</button>}<button className="btn btn-ghost btn-sm" onClick={()=>setDeleteInfo(null)}>Cancel</button></div></div>}
      <div className="admin-day-grid">{lesson.days.map(day=><article className="admin-day-card" key={day.id}><div className="admin-section-title"><h4>Day {day.day_number}: {day.activity_type}</h4><Status value={day.status}/></div><strong>{day.title}</strong><dl><dt>Objectives</dt><dd>{day.learning_objectives?.join('; ')||'Not provided'}</dd><dt>Key concept</dt><dd>{day.key_concept||'Not provided'}</dd><dt>Teaching script</dt><dd>{day.ai_script||'Not provided'}</dd><dt>Real-world context</dt><dd>{day.real_world_context||'Not provided'}</dd><dt>Visual support</dt><dd>{day.visual_support||'Not provided'}</dd><dt>Bible / character</dt><dd>{[day.bible_reference,day.biblical_application,day.character_reference].filter(Boolean).join(' · ')||'Not provided'}</dd><dt>Vocabulary</dt><dd>{day.vocabulary?.join?.(', ')||'Not provided'}</dd><dt>Practice</dt><dd>{day.practice_questions?.join?.('; ')||'Not provided'}</dd></dl><LessonDayEditor day={day} onSaved={state.reload}/></article>)}</div>
    </section></>;
}

function AdminParentAvatar({ parent, size = 40 }) {
  const [source, setSource] = useState('');
  useEffect(() => {
    let objectUrl = '';
    if (parent?.profile_image_url) adminAPI.getParentImage(parent.id).then(({ data }) => {
      objectUrl = URL.createObjectURL(data); setSource(objectUrl);
    }).catch(() => setSource(''));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [parent?.id, parent?.profile_image_url]);
  return <span className="admin-parent-avatar" style={{ width: size, height: size }}>
    {source ? <img src={source} alt="" /> : (parent?.name?.[0] || 'P').toUpperCase()}
  </span>;
}

const EMPTY_PARENT_FORM = { first_name:'', last_name:'', email:'', phone_number:'', address_line_1:'', address_line_2:'', city:'', state_region:'', postal_code:'', country:'' };

function ParentForm({ initial = EMPTY_PARENT_FORM, includeEmail = false, busy, onSubmit, submitLabel }) {
  const [form, setForm] = useState(() => ({ ...EMPTY_PARENT_FORM, ...initial }));
  const set = (key, value) => setForm(old => ({ ...old, [key]: value }));
  return <form className="admin-parent-form" onSubmit={event => { event.preventDefault(); onSubmit(form); }}>
    <div className="admin-form-grid">
      <label>First name<input required value={form.first_name} onChange={e=>set('first_name',e.target.value)}/></label>
      <label>Last name<input required value={form.last_name} onChange={e=>set('last_name',e.target.value)}/></label>
      {includeEmail && <label className="admin-form-wide">Email<input required type="email" value={form.email} onChange={e=>set('email',e.target.value)}/></label>}
      <label>Phone<input value={form.phone_number||''} onChange={e=>set('phone_number',e.target.value)}/></label>
      <label>Country<input value={form.country||''} onChange={e=>set('country',e.target.value)}/></label>
      <label className="admin-form-wide">Address line 1<input value={form.address_line_1||''} onChange={e=>set('address_line_1',e.target.value)}/></label>
      <label className="admin-form-wide">Address line 2<input value={form.address_line_2||''} onChange={e=>set('address_line_2',e.target.value)}/></label>
      <label>City / Town<input value={form.city||''} onChange={e=>set('city',e.target.value)}/></label>
      <label>State / Region<input value={form.state_region||''} onChange={e=>set('state_region',e.target.value)}/></label>
      <label>Postal code<input value={form.postal_code||''} onChange={e=>set('postal_code',e.target.value)}/></label>
    </div>
    <button className="btn btn-primary" disabled={busy}>{busy?'Saving…':submitLabel}</button>
  </form>;
}

function Parents() {
  const navigate=useNavigate();
  const [search,setSearch]=useState(''); const [status,setStatus]=useState(''); const [sort,setSort]=useState('newest'); const [page,setPage]=useState(1);
  const [showCreate,setShowCreate]=useState(false); const [busy,setBusy]=useState(false); const [message,setMessage]=useState('');
  const state=useAdminData(()=>adminAPI.getParents({search,status,sort,page,page_size:20}),[search,status,sort,page]);
  const create=async(form)=>{setBusy(true);setMessage('');try{const response=await adminAPI.createParent(form);setShowCreate(false);setMessage(response.data.message);await state.reload();}catch(e){setMessage(e.response?.data?.detail||'Unable to create parent.');}finally{setBusy(false);}};
  const changeStatus=async(parent,next)=>{if(!window.confirm(`${next==='suspended'?'Suspend':'Reactivate'} ${parent.name}?`))return;setMessage('');try{await adminAPI.updateParentStatus(parent.id,next);setMessage(next==='suspended'?'Parent suspended.':'Parent reactivated.');await state.reload();}catch(e){setMessage(e.response?.data?.detail||'Unable to update parent status.');}};
  if(state.loading)return <Loading/>; if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;
  const data=state.data, pages=parentPageCount(data.total,data.page_size);
  return <>
    <div className="admin-stat-grid">
      <StatCard label="Total Parents" value={data.summary.total_parents} icon={UserRound}/><StatCard label="Active Parents" value={data.summary.active_parents} icon={UserCheck}/><StatCard label="Total Children" value={data.summary.total_children} icon={Users}/><StatCard label="Active Subscriptions" value={null} icon={WalletCards}/>
    </div>
    <section className="card pad"><div className="admin-section-title"><div><h3>Parents</h3><p>Manage parent accounts, children and account information.</p></div><button className="btn btn-primary btn-sm" onClick={()=>setShowCreate(true)}><Plus size={17}/> Add Parent</button></div>
      {message&&<div className="admin-notice">{message}</div>}
      <div className="admin-filters admin-parent-filters"><input placeholder="Search name, email or phone…" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}}/><select value={status} onChange={e=>{setStatus(e.target.value);setPage(1)}}><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option></select><select value={sort} onChange={e=>{setSort(e.target.value);setPage(1)}}><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="name">Name</option><option value="children">Number of children</option></select></div>
      {!data.items.length?<Empty>{search?'Search returned no results.':'No parents found.'}</Empty>:<div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Parent</th><th>Email</th><th>Phone</th><th>Children</th><th>Subscription</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead><tbody>{data.items.map(parent=><tr key={parent.id} className="admin-clickable-row" onClick={()=>navigate(`/admin/parents/${parent.id}`)}><td><div className="admin-parent-cell"><AdminParentAvatar parent={parent}/><strong>{parent.name}</strong></div></td><td>{parent.email}</td><td>{parent.phone_number||'—'}</td><td>{parent.child_count}</td><td><Status value="not_configured"/></td><td><Status value={parent.account_status}/></td><td>{formatDate(parent.created_at)}</td><td onClick={e=>e.stopPropagation()}><div className="admin-row-actions"><button className="btn btn-ghost btn-sm" onClick={()=>navigate(`/admin/parents/${parent.id}`)}>View</button><details><summary aria-label={`More actions for ${parent.name}`}><MoreVertical size={18}/></summary><div className="admin-action-menu"><button onClick={()=>navigate(`/admin/parents/${parent.id}/edit`)}><Pencil size={15}/> Edit</button>{parent.account_status==='active'?<button onClick={()=>changeStatus(parent,'suspended')}><UserX size={15}/> Suspend</button>:<button onClick={()=>changeStatus(parent,'active')}><UserCheck size={15}/> Reactivate</button>}</div></details></div></td></tr>)}</tbody></table></div>}
      <div className="admin-pagination"><button className="btn btn-ghost btn-sm" disabled={page<=1} onClick={()=>setPage(page-1)}>Previous</button><span>Page {page} of {pages} · {data.total} parents</span><button className="btn btn-ghost btn-sm" disabled={page>=pages} onClick={()=>setPage(page+1)}>Next</button></div>
    </section>
    {showCreate&&<div className="admin-modal-backdrop" onClick={()=>setShowCreate(false)}><div className="admin-modal card pad" onClick={e=>e.stopPropagation()}><button className="admin-modal-close" aria-label="Close" onClick={()=>setShowCreate(false)}><X/></button><h3>Add Parent</h3><p>The parent will receive a secure link to choose their password. No plaintext password is sent.</p><ParentForm includeEmail busy={busy} onSubmit={create} submitLabel="Create parent"/></div></div>}
  </>;
}

function ParentDetail({ parentId, editMode=false }) {
  const navigate=useNavigate(); const state=useAdminData(()=>adminAPI.getParent(parentId),[parentId]); const [busy,setBusy]=useState(false); const [message,setMessage]=useState('');
  const save=async(form)=>{setBusy(true);setMessage('');try{await adminAPI.updateParent(parentId,form);setMessage('Parent details updated.');await state.reload();navigate(`/admin/parents/${parentId}`);}catch(e){setMessage(e.response?.data?.detail||'Unable to update parent.');}finally{setBusy(false);}};
  const status=async(next)=>{if(!window.confirm(`${next==='suspended'?'Suspend':'Reactivate'} this parent account?`))return;setBusy(true);try{await adminAPI.updateParentStatus(parentId,next);await state.reload();setMessage(next==='suspended'?'Parent suspended.':'Parent reactivated.');}catch(e){setMessage(e.response?.data?.detail||'Unable to update status.');}finally{setBusy(false);}};
  const reset=async()=>{setBusy(true);setMessage('');try{const response=await adminAPI.sendParentReset(parentId);setMessage(response.data.message);}catch(e){setMessage(e.response?.data?.detail||'Unable to send reset email.');}finally{setBusy(false);}};
  if(state.loading)return <Loading/>; if(state.error)return <ErrorState message={state.error} retry={state.reload}/>; const p=state.data;
  if(editMode)return <><button className="admin-back" onClick={()=>navigate(`/admin/parents/${parentId}`)}><ChevronLeft size={18}/> Back to Parent</button><section className="card pad"><h3>Edit Parent</h3><p>Email remains read-only because verified email changes are not implemented.</p><div className="admin-readonly-email"><strong>Email</strong><span>{p.email}</span></div>{message&&<div className="admin-notice">{message}</div>}<ParentForm initial={p} busy={busy} onSubmit={save} submitLabel="Save changes"/></section></>;
  return <><button className="admin-back" onClick={()=>navigate('/admin/parents')}><ChevronLeft size={18}/> Back to Parents</button>{message&&<div className="admin-notice">{message}</div>}
    <section className="card pad admin-parent-hero"><AdminParentAvatar parent={p} size={72}/><div><h3>{p.name}</h3><p>{p.email}</p><div className="admin-summary"><Status value={p.account_status}/><Status value="not_configured"/></div></div><div className="admin-parent-hero-actions"><button className="btn btn-ghost btn-sm" onClick={()=>navigate(`/admin/parents/${parentId}/edit`)}><Pencil size={16}/> Edit profile</button><button className="btn btn-ghost btn-sm" disabled={busy} onClick={reset}><Mail size={16}/> Send reset link</button>{p.account_status==='active'?<button className="btn btn-ghost btn-sm" disabled={busy} onClick={()=>status('suspended')}><UserX size={16}/> Suspend</button>:<button className="btn btn-ghost btn-sm" disabled={busy} onClick={()=>status('active')}><UserCheck size={16}/> Reactivate</button>}</div></section>
    <div className="admin-grid-2"><section className="card pad"><h3>Personal information</h3><dl className="admin-details"><dt>First name</dt><dd>{p.first_name||'—'}</dd><dt>Last name</dt><dd>{p.last_name||'—'}</dd><dt>Email</dt><dd>{p.email}</dd><dt>Phone</dt><dd>{p.phone_number||'—'}</dd><dt>Address</dt><dd>{[p.address_line_1,p.address_line_2,p.city,p.state_region,p.postal_code,p.country].filter(Boolean).join(', ')||'—'}</dd></dl></section><section className="card pad"><h3>Account information</h3><dl className="admin-details"><dt>Role</dt><dd>{p.role}</dd><dt>Status</dt><dd><Status value={p.account_status}/></dd><dt>Created</dt><dd>{formatDate(p.created_at)}</dd><dt>Last updated</dt><dd>{formatDate(p.updated_at)}</dd></dl></section></div>
    <section className="card pad"><div className="admin-section-title"><div><h3>Children</h3><p>Total Children: {p.total_children}</p></div></div>{!p.children.length?<Empty>This parent has no children yet.</Empty>:<div className="admin-parent-children">{p.children.map(child=><button className="admin-child-card" key={child.id} onClick={()=>navigate(`/admin/students/${child.id}`)}><span className="admin-parent-avatar">{child.avatar}</span><span><strong>{child.name}</strong><small>{child.level_label} · {child.subjects.join(', ')||'No subjects selected'}</small><small>{child.progress_percentage}% progress · {child.login_enabled?'Login enabled':'No direct login'}</small></span><Status value={child.account_status}/></button>)}</div>}</section>
    <section className="card pad"><h3>Subscription</h3><Empty><WalletCards size={32}/><strong>{p.subscription.message}</strong></Empty></section>
  </>;
}

function Students() {
  const navigate=useNavigate(); const state=useAdminData(adminAPI.getStudents,[]); const [query,setQuery]=useState(''); const [level,setLevel]=useState(''); const [status,setStatus]=useState(''); const [subject,setSubject]=useState(''); const [progress,setProgress]=useState('');
  if(state.loading)return <Loading/>; if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;
  const rows=state.data.filter(s=>(!query||`${s.name} ${s.parent}`.toLowerCase().includes(query.toLowerCase()))&&(!level||String(s.level)===level)&&(!subject||s.subjects.includes(subject))&&(!progress||(progress==='not_started'?s.overall_progress===0:progress==='in_progress'?s.overall_progress>0&&s.overall_progress<100:s.overall_progress===100))&&(!status||(status==='needs_support'?s.needs_support:s.status===status)));
  const subjects=[...new Set(state.data.flatMap(s=>s.subjects))];
  return <section className="card pad"><div className="admin-section-title"><div><h3>Students</h3><p>Real student enrollment, activity and learning progress.</p></div><strong>{rows.length} students</strong></div><div className="admin-filters"><input placeholder="Search student or parent…" value={query} onChange={e=>setQuery(e.target.value)}/><select value={level} onChange={e=>setLevel(e.target.value)}><option value="">All levels</option>{Array.from({length:14},(_,i)=><option key={i}>{i}</option>)}</select><select value={subject} onChange={e=>setSubject(e.target.value)}><option value="">All subjects</option>{subjects.map(x=><option key={x}>{x}</option>)}</select><select value={progress} onChange={e=>setProgress(e.target.value)}><option value="">All progress</option><option value="not_started">Not started</option><option value="in_progress">In progress</option><option value="complete">Complete</option></select><select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All activity</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="needs_support">Needs support</option></select></div>{!rows.length?<Empty>No students match these filters.</Empty>:<div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Student</th><th>Parent</th><th>Pathway</th><th>Progress</th><th>Current lesson</th><th>Last active</th><th>Evidence</th><th></th></tr></thead><tbody>{rows.map(s=><tr key={s.id}><td><strong>{s.name}</strong><small><Status value={s.status}/></small></td><td>{s.parent||'—'}</td><td>{s.level_label}<small>{s.education_system} · {s.subjects.join(', ')||'No subjects'}</small></td><td>{s.overall_progress}%</td><td>{s.current_lesson||'Not started'}</td><td>{formatDate(s.last_active)}</td><td>{s.evidence_count}</td><td><button className="btn btn-ghost btn-sm" onClick={()=>navigate(`/admin/students/${s.id}`)}>Open</button></td></tr>)}</tbody></table></div>}</section>;
}

function StudentDetail({ studentId }) {
  const navigate=useNavigate(); const state=useAdminData(()=>adminAPI.getStudent(studentId),[studentId]); if(state.loading)return <Loading/>; if(state.error)return <ErrorState message={state.error} retry={state.reload}/>; const d=state.data,s=d.student;
  return <><button className="admin-back" onClick={()=>navigate('/admin/students')}><ChevronLeft size={18}/> Back to Students</button><div className="admin-grid-2"><section className="card pad"><h3>{s.avatar} {s.name}</h3><p>{s.level_label} · {s.education_system}</p><dl className="admin-details"><dt>Parent</dt><dd>{s.parent} ({s.parent_email})</dd><dt>Subjects</dt><dd>{s.subjects.join(', ')||'None'}</dd><dt>Account</dt><dd>{s.active?'Active':'Inactive'}</dd></dl></section><section className="card pad"><h3>Certificates</h3><Empty>No certificates have been issued.</Empty></section></div><section className="card pad"><h3>Progress</h3>{!d.progress.length?<Empty>No lesson progress yet.</Empty>:<div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Lesson</th><th>Day</th><th>Status</th><th>Score</th><th>Mastery</th></tr></thead><tbody>{d.progress.map((p,i)=><tr key={i}><td>{p.lesson}</td><td>{p.day}</td><td><Status value={p.status}/></td><td>{p.score??'—'}</td><td>{p.mastery}</td></tr>)}</tbody></table></div>}</section><div className="admin-grid-2"><section className="card pad"><h3>Learning Evidence</h3>{!d.evidence.length?<Empty>No learning evidence has been submitted yet.</Empty>:d.evidence.slice(0,8).map(e=><div className="admin-list-row" key={e.id}><div><strong>{e.skill}</strong><small>{e.subject} · {e.lesson}</small></div><Status value={e.status}/></div>)}</section><section className="card pad"><h3>AI Tutor Activity</h3>{!d.sessions.length?<Empty>No tutor sessions yet.</Empty>:d.sessions.map(x=><div className="admin-list-row" key={x.id}><div><strong>{x.lesson} · Day {x.day}</strong><small>{x.phase} · {x.remediation_count} remediations</small></div><Status value={x.practice_ready?'practice_ready':'in_progress'}/></div>)}</section></div></>;
}

function Evidence() {
  const state=useAdminData(adminAPI.getEvidence,[]); const [filters,setFilters]=useState({search:'',status:'',type:'',submission:'',date:''}); const [selected,setSelected]=useState(null); const [message,setMessage]=useState('');
  if(state.loading)return <Loading/>; if(state.error)return <ErrorState message={state.error} retry={state.reload}/>; const rows=state.data.filter(e=>(!filters.search||`${e.student} ${e.subject} ${e.lesson}`.toLowerCase().includes(filters.search.toLowerCase()))&&(!filters.status||e.status===filters.status)&&(!filters.type||e.evidence_type===filters.type)&&(!filters.submission||e.submission_type===filters.submission)&&(!filters.date||String(e.created_at).slice(0,10)===filters.date));
  const retry=async(item)=>{try{await evidenceAPI.retryEvaluation(item.id);setMessage('Evaluation retry completed.');setSelected(null);await state.reload();}catch(e){setMessage(e.response?.data?.detail||'Retry failed.');}};
  return <section className="card pad"><div className="admin-section-title"><div><h3>Learning Evidence</h3><p>Review submitted work without exposing unnecessary private data.</p></div><strong>{rows.length} records</strong></div>{message&&<div className="admin-notice">{message}</div>}<div className="admin-filters"><input placeholder="Student, subject or lesson…" value={filters.search} onChange={e=>setFilters({...filters,search:e.target.value})}/><select value={filters.status} onChange={e=>setFilters({...filters,status:e.target.value})}><option value="">All statuses</option><option>pending</option><option>verified</option><option value="needs_review">Needs review</option></select><select value={filters.type} onChange={e=>setFilters({...filters,type:e.target.value})}><option value="">All evidence types</option><option>lesson</option><option>project</option><option>real-world</option></select><select value={filters.submission} onChange={e=>setFilters({...filters,submission:e.target.value})}><option value="">All submissions</option><option>text</option><option>image</option><option>audio</option><option>video</option><option>file</option></select><input type="date" value={filters.date} onChange={e=>setFilters({...filters,date:e.target.value})}/></div>{!rows.length?<Empty>No learning evidence has been submitted yet.</Empty>:<div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Student</th><th>Subject / Lesson</th><th>Type</th><th>Date</th><th>Score</th><th>Status</th><th></th></tr></thead><tbody>{rows.map(e=><tr key={e.id}><td>{e.student}</td><td><strong>{e.skill}</strong><small>{e.subject} · {e.lesson}</small></td><td>{e.evidence_type} / {e.submission_type}</td><td>{formatDate(e.created_at)}</td><td>{e.score??'—'}</td><td><Status value={e.status}/></td><td><button className="btn btn-ghost btn-sm" onClick={()=>setSelected(e)}>Details</button></td></tr>)}</tbody></table></div>}{selected&&<div className="admin-modal-backdrop" onClick={()=>setSelected(null)}><div className="admin-modal card pad" onClick={e=>e.stopPropagation()}><button className="admin-modal-close" onClick={()=>setSelected(null)}><X/></button><h3>{selected.skill}</h3><p>{selected.student} · {selected.subject} · {selected.lesson}</p><h4>Submission</h4><p>{selected.content|| (selected.has_file?'File submission':'No text content')}</p><h4>AI feedback</h4><p>{selected.feedback||'No feedback yet.'}</p>{selected.status!=='verified'&&<button className="btn btn-primary btn-sm" onClick={()=>retry(selected)}>Retry authorized evaluation</button>}</div></div>}</section>;
}

function Analytics() { const state=useAdminData(adminAPI.getAnalytics,[]); if(state.loading)return <Loading/>;if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;const d=state.data;return <><div className="admin-stat-grid"><StatCard label="Lessons Started" value={d.engagement.lessons_started} icon={Activity}/><StatCard label="Lessons Completed" value={d.engagement.lessons_completed} icon={FileCheck2}/><StatCard label="Average Completion" value={`${d.engagement.average_progress}%`} icon={BarChart3}/><StatCard label="Remediation Records" value={d.academic.remediation_frequency} icon={GraduationCap}/></div><div className="admin-grid-2"><section className="card pad"><h3>Mastery distribution</h3>{!Object.keys(d.academic.mastery_distribution).length?<Empty>Not enough data yet.</Empty>:Object.entries(d.academic.mastery_distribution).map(([k,v])=><div className="admin-list-row" key={k}><span>{k}</span><strong>{v}</strong></div>)}</section><section className="card pad"><h3>Completion by subject</h3>{!Object.keys(d.academic.completion_by_subject).length?<Empty>Not enough data yet.</Empty>:Object.entries(d.academic.completion_by_subject).map(([k,v])=><div className="admin-list-row" key={k}><span>{k}</span><strong>{v}</strong></div>)}</section></div><section className="card pad"><h3>AI usage</h3><div className="admin-summary"><span><strong>{d.ai_usage.tutor_sessions}</strong> tutor sessions</span><span><strong>{d.ai_usage.ai_interactions}</strong> interactions</span><span><strong>{d.ai_usage.evaluations}</strong> evaluation retries</span><span><strong>Not tracked</strong> failed requests / voice usage</span></div></section></> }

function Reports() { const state=useAdminData(adminAPI.getReports,[]);const [message,setMessage]=useState('');if(state.loading)return <Loading/>;if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;const download=async(row)=>{try{const res=await reportsAPI.getStudentReport(row.student_id);const blob=new Blob([JSON.stringify(res.data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${row.student.replaceAll(' ','-').toLowerCase()}-progress-report.json`;a.click();URL.revokeObjectURL(url);}catch(e){setMessage(e.response?.data?.detail||'Report failed.');}};return <section className="card pad"><h3>Reports</h3><p>Download real student progress and evidence data. PDF generation is not currently implemented.</p>{message&&<div className="admin-notice">{message}</div>}{!state.data.length?<Empty>No student reports are available yet.</Empty>:state.data.map(r=><div className="admin-list-row" key={r.student_id}><div><strong>{r.student}</strong><small>{r.parent||'No parent'} · {r.completed_lessons} completed · {r.evidence_count} evidence</small></div><button className="btn btn-ghost btn-sm" onClick={()=>download(r)}>Download JSON</button></div>)}</section> }

function Earnings() { return <section className="card pad"><h3>Earnings / Subscriptions</h3><Empty><WalletCards size={36}/><strong>Subscription billing is not connected yet.</strong><span>Stripe must be implemented before plans, payments, renewals, subscriptions, or revenue can be reported.</span></Empty><div className="admin-plan-grid">{['Basic','Premium','Elite','Free Trial'].map(x=><div className="admin-plan" key={x}><strong>{x}</strong><span>Not configured</span></div>)}</div></section> }
function Content() { const state=useAdminData(adminAPI.getContent,[]);if(state.loading)return <Loading/>;if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;return <section className="card pad"><h3>Supporting Content</h3><div className="admin-summary"><span><strong>{state.data.reading_recommendations}</strong> reading recommendations</span><span><strong>Curriculum-linked</strong> Bible and character resources</span></div><Empty>{state.data.message}</Empty></section> }
function AIMonitoring() { const state=useAdminData(adminAPI.getAIMonitoring,[]);if(state.loading)return <Loading/>;if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;const d=state.data;return <><div className="admin-stat-grid"><StatCard label="Tutor Sessions" value={d.tutor_sessions} icon={Bot}/><StatCard label="AI Interactions" value={d.ai_interactions} icon={Activity}/><StatCard label="Pending Evaluations" value={d.pending_evaluations} icon={FileCheck2}/><StatCard label="Remediation Count" value={d.total_remediations} icon={GraduationCap}/></div><div className="admin-grid-2"><section className="card pad"><h3>Provider configuration</h3>{Object.entries(d.services).map(([k,v])=><div className="admin-list-row" key={k}><span>{k.replaceAll('_',' ')}</span><Status value={v?'configured':'not_configured'}/></div>)}</section><section className="card pad"><h3>Operational tracking</h3><p>OpenAI failure count: Not tracked</p><p>TTS failure count: Not tracked</p><p>No API keys or student transcripts are exposed here.</p></section></div></> }
function SettingsPage({navigate}) { const state=useAdminData(adminAPI.getSettings,[]);if(state.loading)return <Loading/>;if(state.error)return <ErrorState message={state.error} retry={state.reload}/>;const d=state.data;return <><SettingsNav section="platform" navigate={navigate}/><div className="admin-grid-2"><section className="card pad"><h3>Platform</h3><div className="admin-list-row"><span>Name</span><strong>{d.platform.name}</strong></div><div className="admin-list-row"><span>Official domain</span><strong>{d.platform.domain}</strong></div><div className="admin-list-row"><span>Support email</span><strong>{d.platform.support_email}</strong></div><div className="admin-list-row"><span>Environment</span><strong>{d.platform.environment}</strong></div></section><section className="card pad"><h3>AI and voice</h3><div className="admin-list-row"><span>OpenAI</span><Status value={d.ai.openai}/></div><div className="admin-list-row"><span>Text model</span><strong>{d.ai.openai_model||'Not configured'}</strong></div><div className="admin-list-row"><span>OpenAI Realtime</span><Status value={d.ai.realtime}/></div><div className="admin-list-row"><span>Realtime model</span><strong>{d.ai.realtime_model||'Not configured'}</strong></div><div className="admin-list-row"><span>Classroom voice</span><strong>{d.ai.active_voice_provider}</strong></div><div className="admin-list-row"><span>ElevenLabs in active classroom</span><Status value={d.ai.elevenlabs_active_classroom?'active':'not_active'}/></div></section><section className="card pad"><h3>Academic</h3><p>{d.academic.education_systems.join(', ')}</p><p>Levels 0–13</p><p>{d.academic.subjects.join(', ')||'No subjects configured'}</p></section><section className="card pad"><h3>Subscriptions</h3><Status value={d.subscriptions.stripe}/><p>Secrets are never displayed.</p></section></div></> }

export default function AdminDashboardScreen({ currentUser, onProfileUpdated, onExit }) {
  const location=useLocation(),navigate=useNavigate(); const [drawer,setDrawer]=useState(false); const [collapsed,setCollapsed]=useState(false); const [accountOpen,setAccountOpen]=useState(false); const [adminProfile,setAdminProfile]=useState(null); const [adminImage,setAdminImage]=useState(null);
  const loadAdminProfile=async()=>{try{const {data}=await adminAPI.getProfile();setAdminProfile(data);onProfileUpdated?.(data);try{const image=await adminAPI.getProfileImage();setAdminImage(old=>{if(old)URL.revokeObjectURL(old);return URL.createObjectURL(image.data)})}catch(e){setAdminImage(old=>{if(old)URL.revokeObjectURL(old);return null})}return data}catch(e){return null}};
  useEffect(()=>{loadAdminProfile();return()=>{if(adminImage)URL.revokeObjectURL(adminImage)}},[]);
  const segments=location.pathname.split('/').filter(Boolean); const detailId=segments[2]; const base=segments[1]||'';
  const title=base==='profile'?'Profile':NAV.find(([,path])=>path==='/admin'?location.pathname==='/admin':location.pathname.startsWith(path))?.[0]||'Admin';
  let page=<Overview/>;
  if(base==='curriculum') page=detailId?<CurriculumDetail lessonId={detailId}/>:<Curriculum/>;
  else if(base==='parents') page=detailId?<ParentDetail parentId={detailId} editMode={segments[3]==='edit'}/>:<Parents/>;
  else if(base==='students') page=detailId?<StudentDetail studentId={detailId}/>:<Students/>;
  else if(base==='evidence') page=<Evidence/>; else if(base==='analytics') page=<Analytics/>; else if(base==='reports') page=<Reports/>;
  else if(base==='earnings') page=<Earnings/>; else if(base==='content') page=<Content/>; else if(base==='ai-monitoring') page=<AIMonitoring/>; else if(base==='profile') page=<AdminProfileOverview profile={adminProfile} imageUrl={adminImage} navigate={navigate}/>; else if(base==='settings'&&detailId==='profile') page=<AdminProfileForm profile={adminProfile} imageUrl={adminImage} navigate={navigate} onSaved={loadAdminProfile}/>; else if(base==='settings'&&detailId==='security') page=<AdminSecurity navigate={navigate} onExit={onExit}/>; else if(base==='settings') page=<SettingsPage navigate={navigate}/>;
  const initials=`${adminProfile?.first_name?.[0]||currentUser?.name?.[0]||'A'}${adminProfile?.last_name?.[0]||''}`;
  return <div className={`admin-shell ${collapsed?'collapsed':''} ${drawer?'drawer-open':''}`}><aside className="sidebar"><div className="admin-sidebar-head"><BrandLogo variant="adaptive" color="#fff"/><button className="admin-nav-close" onClick={()=>setDrawer(false)}><X/></button></div><nav>{NAV.map(([label,path,Icon])=>{const active=path==='/admin'?location.pathname==='/admin':location.pathname.startsWith(path);return <button key={path} className={`side-link ${active?'on':''}`} onClick={()=>{navigate(path);setDrawer(false)}} title={label}><Icon size={19}/><span>{label}</span></button>})}</nav><div className="admin-sidebar-bottom"><button className="side-link" onClick={()=>setCollapsed(!collapsed)}><ChevronLeft className={collapsed?'flip':''} size={19}/><span>Collapse</span></button><button className="side-link" onClick={onExit}><X size={19}/><span>Exit Admin</span></button></div></aside><button className="admin-drawer-scrim" aria-label="Close menu" onClick={()=>setDrawer(false)}/><main className="admin-main"><header className="admin-topbar"><div className="admin-title"><button className="admin-menu" onClick={()=>setDrawer(true)}><Menu/></button><div><small>HomeWiseEdu Admin</small><h2>{title}</h2></div></div><div className="admin-header-tools"><div className="admin-global-search"><Search size={17}/><input placeholder="Search within the current page"/></div><div className="admin-account"><button className="admin-account-trigger" onClick={()=>setAccountOpen(!accountOpen)} aria-label="Open administrator account menu">{adminImage?<img src={adminImage} alt="Administrator"/>:<span>{initials}</span>}</button>{accountOpen&&<div className="admin-account-menu"><div className="admin-account-summary">{adminImage?<img src={adminImage} alt=""/>:<span>{initials}</span>}<div><strong>{adminProfile?.name||currentUser?.name||'Administrator'}</strong><small>Administrator</small></div></div><button onClick={()=>{navigate('/admin/profile');setAccountOpen(false)}}><UserRound size={17}/> View Profile</button><button onClick={()=>{navigate('/admin/settings');setAccountOpen(false)}}><Settings size={17}/> Settings</button><hr/><button onClick={onExit}><X size={17}/> Logout</button></div>}</div></div></header><div className="admin-body">{page}</div></main></div>;
}
