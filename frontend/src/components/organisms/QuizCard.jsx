import React from 'react';

export default function QuizCard({
  questionNumber = 1,
  totalQuestions = 3,
  questionData,
  selectedOption,
  isAnswered,
  onSelectOption,
  onSubmitAnswer,
}) {
  if (!questionData) return null;

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', width: '100%' }}>
      <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--grape)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 8 }}>
        Question {questionNumber} of {totalQuestions}
      </div>

      <div className="quiz-card">
        <div className="quiz-q">
          <div className="lab">Quiz</div>
          <h2>{questionData.question}</h2>
        </div>

        <div className="quiz-opts">
          {questionData.options?.map((opt, i) => {
            const isSel = selectedOption === opt;
            const isCorrect = opt === questionData.correct_answer;
            let optClass = 'qopt';

            if (isAnswered) {
              if (isCorrect) optClass += ' correct';
              else if (isSel) optClass += ' wrong';
            } else if (isSel) {
              optClass += ' sel';
            }

            return (
              <button
                key={i}
                className={optClass}
                onClick={() => onSelectOption(opt)}
                disabled={isAnswered}
              >
                <div className="qb">
                  {isAnswered && isCorrect ? '✓' : isAnswered && isSel ? '✗' : isSel ? '●' : ''}
                </div>
                {opt}
              </button>
            );
          })}

          {!isAnswered && (
            <button
              className="quiz-submit"
              disabled={!selectedOption}
              onClick={onSubmitAnswer}
            >
              Submit answer →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
