export async function advanceAfterFeedback(playFeedback, feedbackText, advance) {
  const completed = await playFeedback(feedbackText);
  if (completed) advance();
  return completed;
}
