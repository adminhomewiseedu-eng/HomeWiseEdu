const QUESTION_PHASES = new Set([
  'GREETING',
  'UNDERSTANDING_CHECK',
  'GUIDED_PRACTICE',
  'APPLICATION',
  'MASTERY_CHECK',
]);

const AUTHORITATIVE_DELIVERY_PHASES = new Set([
  'TEACHING',
  'WORKED_EXAMPLE_1',
  'WORKED_EXAMPLE_2',
  'WORKED_EXAMPLE_3',
  'LESSON_SUMMARY',
]);

export function teacherDeliveryLooksComplete(phase, transcript) {
  const text = String(transcript || '').trim();
  if (!/[\p{L}\p{N}]/u.test(text)) return false;
  if (AUTHORITATIVE_DELIVERY_PHASES.has(phase)) return true;
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
