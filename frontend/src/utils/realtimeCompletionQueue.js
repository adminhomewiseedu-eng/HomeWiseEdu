export function deferRealtimeCompletion(pendingRef, completion) {
  pendingRef.current = completion;
}

export function drainRealtimeCompletion(pendingRef, canProcess, processCompletion) {
  const completion = pendingRef.current;
  if (!completion || !canProcess) return false;
  pendingRef.current = null;
  processCompletion(completion);
  return true;
}
