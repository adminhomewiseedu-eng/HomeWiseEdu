const HESITATION_ENDINGS = /\b(um+|uh+|erm+|hmm+|because|so|and|but|i think|maybe)\s*[,.…-]*$/i;
const COMPLETE_ENDING = /[.!?]\s*$/;

export function adaptiveSilenceMs(transcript) {
  const text = String(transcript || '').trim();
  if (!text) return 3200;
  if (HESITATION_ENDINGS.test(text)) return 3800;
  const words = text.split(/\s+/).filter(Boolean).length;
  if (words <= 2) return 3200;
  if (COMPLETE_ENDING.test(text)) return 2200;
  return 2800;
}

export function isStableBargeCandidate(previous, current) {
  const before = String(previous || '').trim().toLowerCase();
  const now = String(current || '').trim().toLowerCase();
  if (!now) return false;
  if (!before) return true;
  return now === before || now.startsWith(before) || before.startsWith(now);
}

const normalizedVoiceWords = (text) => String(text || '')
  .toLowerCase()
  .replace(/[^a-z0-9' ]/g, ' ')
  .split(/\s+/)
  .filter((word) => word.length > 2);

export function looksLikeTeacherEcho(transcript, teacherSpeech) {
  const heardWords = normalizedVoiceWords(transcript);
  if (!heardWords.length) return true;

  // Short learner interjections such as "wait", "why?", or "five" are valid
  // barge-ins. There is not enough signal to classify them safely as echo.
  if (heardWords.length < 4) return false;

  const teacherWords = normalizedVoiceWords(teacherSpeech);
  if (!teacherWords.length) return false;

  const heardPhrase = heardWords.join(' ');
  const teacherPhrase = teacherWords.join(' ');
  if (teacherPhrase.includes(heardPhrase)) return true;

  const teacherSet = new Set(teacherWords);
  const overlap = heardWords.filter((word) => teacherSet.has(word)).length / heardWords.length;
  return overlap >= 0.8;
}
