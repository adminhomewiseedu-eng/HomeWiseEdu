const QUESTION_PHASES = new Set([
  'GREETING',
  'TEACHING',
  'WORKED_EXAMPLE_1',
  'WORKED_EXAMPLE_2',
  'WORKED_EXAMPLE_3',
]);

const MINIMUM_WORDS = {
  GREETING: 12,
  TEACHING: 24,
  WORKED_EXAMPLE_1: 20,
  WORKED_EXAMPLE_2: 20,
  WORKED_EXAMPLE_3: 20,
  LESSON_SUMMARY: 12,
};

export function teacherDeliveryLooksComplete(phase, transcript) {
  const text = String(transcript || '').trim();
  const minimum = MINIMUM_WORDS[phase];
  if (!minimum) return false;
  if (text.split(/\s+/).filter(Boolean).length < minimum) return false;
  if (QUESTION_PHASES.has(phase) && !text.includes('?')) return false;
  return true;
}
