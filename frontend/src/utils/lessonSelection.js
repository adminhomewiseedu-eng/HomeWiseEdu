export function filterSessions(sessions, subject = '', week = '', unit = '') {
  return sessions.filter(s => (!subject || String(s.subject_id) === subject) &&
    (!week || (week === 'unknown' ? s.curriculum_week == null : String(s.curriculum_week) === week)) &&
    (!unit || String(s.unit_id) === unit));
}

export function weekLabel(week) {
  return week == null ? 'Week not supplied' : `Week ${week}`;
}

export function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function prioritizedAssignments(assignments, today = localDate()) {
  return assignments.filter(a => a.status !== 'completed').sort((a, b) =>
    Number(a.scheduled_date > today) - Number(b.scheduled_date > today) ||
    a.scheduled_date.localeCompare(b.scheduled_date) || a.priority - b.priority || a.assignment_id - b.assignment_id);
}
