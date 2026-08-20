export function resolveLessonResume(sessionData = {}) {
  const state = sessionData.pedagogical_state || {};
  if (!Object.keys(state).length) return { mode: 'new' };
  if (sessionData.practice_ready === true) return { mode: 'complete', state };
  if (state.active_question && state.active_phase === state.current_phase) {
    return { mode: 'active_question', state, question: state.active_question };
  }
  return { mode: 'resume_phase', state };
}
