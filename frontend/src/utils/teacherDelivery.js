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
  if (/\b(?:find|fetch|pick up|hold up|describe)\b[^.!?]{0,60}\bobjects?\b/i.test(text)) return false;
  if (QUESTION_PHASES.has(phase) && !text.includes('?')) return false;
  if (QUESTION_PHASES.has(phase) && phase !== 'GREETING') {
    const questionEnd = text.lastIndexOf('?');
    const beforeQuestion = text.slice(0, questionEnd);
    const questionStart = Math.max(
      beforeQuestion.lastIndexOf('.'),
      beforeQuestion.lastIndexOf('!'),
      beforeQuestion.lastIndexOf('?'),
    );
    const finalQuestion = text.slice(questionStart + 1, questionEnd + 1).trim().toLowerCase();
    const asksForAcademicResponse = /\b(what|how|which|where|why|how many)\b/.test(finalQuestion)
      || /\b(?:can|could|will|would) you\s+(?:count|tell|explain|show|say|find|solve|work|try)\b/.test(finalQuestion);
    if (!asksForAcademicResponse) return false;
  }
  return true;
}
