const TEACHER_PHASES = new Set([
  'TEACHING',
  'WORKED_EXAMPLE_1',
  'WORKED_EXAMPLE_2',
  'WORKED_EXAMPLE_3',
]);

const ACADEMIC_PHASES = new Set([
  'UNDERSTANDING_CHECK',
  'GUIDED_PRACTICE',
  'APPLICATION',
  'MASTERY_CHECK',
]);

export function nextAuthoritativeRealtimeTurn(previousPhase, state) {
  const phase = state?.current_phase;
  if (!phase || state?.practice_ready) return null;

  // The opening greeting intentionally waits for the learner. Every later
  // teacher-led boundary continues from backend authority without requiring a
  // meaningless "continue" utterance.
  if (TEACHER_PHASES.has(phase) && previousPhase !== 'GREETING') {
    return { tag: 'teacher_delivery', phase };
  }

  // A newly-entered academic phase needs its backend-bound question spoken
  // once. Once active_question is persisted, silence is intentional.
  if (ACADEMIC_PHASES.has(phase) && !state.active_question) {
    return { tag: 'academic_prompt', phase };
  }

  return null;
}
