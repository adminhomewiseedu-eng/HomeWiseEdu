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
