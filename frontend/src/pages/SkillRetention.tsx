import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Brain, 
  Clock, 
  Calendar, 
  AlertCircle, 
  CheckCircle2, 
  Play, 
  Sparkles, 
  X, 
  Check, 
  ArrowRight,
  TrendingDown,
  Target
} from 'lucide-react';
import { retentionApi, type RetentionSkill, type TestQuestion } from '../api/retention';

export default function SkillRetention() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['skill-retention-status'],
    queryFn: retentionApi.getStatus,
    refetchOnWindowFocus: true,
  });

  // Test Modal State
  const [activeSkillForTest, setActiveSkillForTest] = useState<string | null>(null);
  const [testQuestions, setTestQuestions] = useState<TestQuestion[]>([]);
  const [selectedAnswers, setSelectedAnswers] = useState<number[]>([]);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [timeLeft, setTimeLeft] = useState(180);
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<any | null>(null);

  // Timer countdown during test
  useEffect(() => {
    let timer: any;
    if (activeSkillForTest && !testResult && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [activeSkillForTest, testResult, timeLeft]);

  const handleLaunchTest = async (skill: string) => {
    setActiveSkillForTest(skill);
    setTestLoading(true);
    setTestResult(null);
    setSelectedAnswers([]);
    setCurrentQuestionIdx(0);
    setTimeLeft(180);

    try {
      const response = await retentionApi.startTest(skill);
      setTestQuestions(response.questions);
      setSelectedAnswers(new Array(response.questions.length).fill(-1));
    } catch (err) {
      console.error('Failed to start retention test:', err);
    } finally {
      setTestLoading(false);
    }
  };

  const handleSelectOption = (optIdx: number) => {
    const updated = [...selectedAnswers];
    updated[currentQuestionIdx] = optIdx;
    setSelectedAnswers(updated);
  };

  const submitMutation = useMutation({
    mutationFn: (variables: { skill: string; answers: number[] }) =>
      retentionApi.submitTest(variables.skill, variables.answers),
    onSuccess: (result) => {
      setTestResult(result);
      queryClient.invalidateQueries({ queryKey: ['skill-retention-status'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });

  const handleSubmitTest = () => {
    if (!activeSkillForTest) return;
    submitMutation.mutate({
      skill: activeSkillForTest,
      answers: selectedAnswers,
    });
  };

  const closeTestModal = () => {
    setActiveSkillForTest(null);
    setTestResult(null);
    setTestQuestions([]);
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const prompt = data?.prompt_notification;
  const skills = data?.skills || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200 mb-3">
            <Brain className="w-3.5 h-3.5 text-purple-600" /> Ebbinghaus Forgetting Curve & Spaced Repetition
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Skill Decay & Retention Engine</h1>
          <p className="text-slate-500 mt-1 text-sm max-w-2xl">
            CareerMind models technical memory retention over time. Rapid 3-minute diagnostic tests verify long-term retention, automatically scheduling revisions when concepts decay.
          </p>
        </div>

        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200 p-4 rounded-xl shadow-xs">
          <div className="text-right">
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Average Retention</div>
            <div className={`text-3xl font-extrabold ${
              (data?.overall_retention || 78) >= 80 ? 'text-emerald-600' : (data?.overall_retention || 78) >= 65 ? 'text-amber-600' : 'text-rose-600'
            }`}>
              {data?.overall_retention || 78}%
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600 shadow-xs">
            <TrendingDown className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Retention Prompt Notification Banner (if any skill is decaying) */}
      {prompt && (
        <div className="p-6 rounded-2xl border border-amber-200 bg-amber-50/70 flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in slide-in-from-top-3 duration-500 shadow-xs">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-amber-700 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Retention Test Recommended
              </div>
              <h3 className="text-base font-semibold text-slate-900 mt-0.5">{prompt.message}</h3>
              <p className="text-xs text-slate-600 mt-1">
                Taking a 3-minute refresher will reset your memory decay curve and prevent interview knowledge drops.
              </p>
            </div>
          </div>

          <button
            onClick={() => handleLaunchTest(prompt.skill)}
            className="px-5 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold text-xs uppercase tracking-wider transition-all shadow-xs flex items-center gap-2 shrink-0 self-start md:self-center"
          >
            <Play className="w-3.5 h-3.5 fill-current" /> Start 3-Min Test
          </button>
        </div>
      )}

      {/* Tracked Skills Cards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Tracked Engineering Competencies & Memory Status
          </h2>
          <span className="text-xs text-slate-500">{skills.length} Tracked Skills</span>
        </div>

        {isLoading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-slate-500">Calculating memory decay curves...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {skills.map((item: RetentionSkill) => {
              const isDecaying = item.decay_status === 'degrading' || item.decay_status === 'critical';
              return (
                <div
                  key={item.skill}
                  className={`p-6 rounded-2xl border bg-white shadow-xs transition-all hover:shadow-md flex flex-col justify-between space-y-5 ${
                    item.decay_status === 'critical'
                      ? 'border-rose-300 ring-1 ring-rose-200'
                      : item.decay_status === 'degrading'
                      ? 'border-amber-300 ring-1 ring-amber-200'
                      : 'border-slate-200'
                  }`}
                >
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                          {item.category}
                        </span>
                        <h3 className="text-lg font-bold text-slate-900 mt-0.5">{item.skill}</h3>
                      </div>
                      <div className="text-right">
                        <div className={`text-2xl font-black font-mono ${
                          item.current_retention >= 80 ? 'text-emerald-600' : item.current_retention >= 65 ? 'text-amber-600' : 'text-rose-600'
                        }`}>
                          {item.current_retention}%
                        </div>
                        <div className="text-[10px] uppercase font-semibold text-slate-400">Retention</div>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          item.current_retention >= 80 ? 'bg-emerald-500' : item.current_retention >= 65 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${item.current_retention}%` }}
                      />
                    </div>

                    {/* Timeline Info */}
                    <div className="space-y-2 text-xs pt-1">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-blue-600" /> Last Practiced:
                        </span>
                        <span className="font-semibold text-slate-800">{item.last_practiced} ({item.days_elapsed}d ago)</span>
                      </div>

                      <div className="flex items-center justify-between text-slate-500">
                        <span className="flex items-center gap-1.5">
                          <Brain className="w-3.5 h-3.5 text-purple-600" /> Retention Status:
                        </span>
                        <span className={`font-semibold ${
                          item.decay_status === 'fresh' ? 'text-emerald-600' : item.decay_status === 'degrading' ? 'text-amber-600' : 'text-rose-600'
                        }`}>
                          {item.status_label}
                        </span>
                      </div>

                      {item.revision_scheduled && (
                        <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-200 text-purple-800 flex items-center justify-between text-xs">
                          <span className="flex items-center gap-1.5">
                            <Clock className="w-3 h-3 text-purple-600" /> Revision Due:
                          </span>
                          <span className="font-semibold">{item.revision_scheduled}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="pt-2">
                    <button
                      onClick={() => handleLaunchTest(item.skill)}
                      className={`w-full py-2.5 px-4 rounded-xl font-semibold text-xs transition-all flex items-center justify-center gap-2 border ${
                        isDecaying
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-blue-600 shadow-xs hover:opacity-95'
                          : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Take 3-Min Retention Test
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3-Minute Retention Test Modal */}
      {activeSkillForTest && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-white border border-slate-200 rounded-2xl p-6 md:p-8 shadow-xl relative space-y-6 max-h-[90vh] overflow-y-auto">
            {/* Close button */}
            <button
              onClick={closeTestModal}
              className="absolute top-6 right-6 p-2 rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {testLoading ? (
              <div className="py-20 flex flex-col items-center justify-center space-y-3">
                <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-slate-500">Generating 3-minute diagnostic test for {activeSkillForTest}...</span>
              </div>
            ) : testResult ? (
              /* Test Result View */
              <div className="space-y-6 text-center animate-in zoom-in-95 duration-300">
                <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center ${
                  testResult.score_percentage >= 70 ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-rose-50 text-rose-600 border border-rose-200'
                }`}>
                  {testResult.score_percentage >= 70 ? <CheckCircle2 className="w-8 h-8" /> : <AlertCircle className="w-8 h-8" />}
                </div>

                <div>
                  <h3 className="text-2xl font-bold text-slate-900">{activeSkillForTest} Retention Evaluated</h3>
                  <p className="text-sm text-slate-500 mt-1">{testResult.feedback}</p>
                </div>

                {/* Score and Retention delta */}
                <div className="grid grid-cols-3 gap-3 max-w-md mx-auto">
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Test Score</div>
                    <div className="text-2xl font-bold text-blue-600 mt-0.5">{testResult.score_percentage}%</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Old Retention</div>
                    <div className="text-2xl font-bold text-slate-400 mt-0.5">{testResult.old_retention}%</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">New Retention</div>
                    <div className={`text-2xl font-bold mt-0.5 ${
                      testResult.new_retention >= 80 ? 'text-emerald-600' : testResult.new_retention >= 65 ? 'text-amber-600' : 'text-rose-600'
                    }`}>
                      {testResult.new_retention}%
                    </div>
                  </div>
                </div>

                {/* Revision Scheduled Notification */}
                {testResult.revision_scheduled && (
                  <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 text-purple-900 text-xs flex items-center justify-between text-left">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-purple-600 shrink-0" />
                      <span>Automatic revision scheduled on <strong>{testResult.revision_scheduled}</strong> to reverse memory decay.</span>
                    </div>
                  </div>
                )}

                {/* Targeted Questions for Revision */}
                {testResult.targeted_revision_questions && testResult.targeted_revision_questions.length > 0 && (
                  <div className="text-left space-y-2 p-5 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="text-xs font-semibold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-blue-600" /> Targeted Revision Drills Generated
                    </div>
                    <ul className="text-xs text-slate-700 space-y-2">
                      {testResult.targeted_revision_questions.map((q: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-blue-600 font-bold">{i + 1}.</span>
                          <span>{q}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-2">
                  <button
                    onClick={closeTestModal}
                    className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-sm hover:opacity-95 transition-all shadow-xs"
                  >
                    Done & Return to Retention Dashboard
                  </button>
                </div>
              </div>
            ) : testQuestions.length > 0 ? (
              /* Active Test View */
              <div className="space-y-6">
                {/* Header & Timer */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                      3-Minute Retention Drill
                    </span>
                    <h3 className="text-xl font-bold text-slate-900 mt-0.5">{activeSkillForTest} Test</h3>
                  </div>

                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 font-mono text-sm font-bold text-slate-900">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <span>{formatTimer(timeLeft)}</span>
                  </div>
                </div>

                {/* Progress Indicators */}
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Question {currentQuestionIdx + 1} of {testQuestions.length}</span>
                  <span>{selectedAnswers.filter((a) => a !== -1).length} of {testQuestions.length} Answered</span>
                </div>

                {/* Question Text */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <h4 className="text-base font-semibold text-slate-900 leading-snug">
                    {testQuestions[currentQuestionIdx]?.question}
                  </h4>
                </div>

                {/* Options */}
                <div className="space-y-2.5">
                  {testQuestions[currentQuestionIdx]?.options.map((opt: string, optIdx: number) => {
                    const isSelected = selectedAnswers[currentQuestionIdx] === optIdx;
                    return (
                      <button
                        key={optIdx}
                        onClick={() => handleSelectOption(optIdx)}
                        className={`w-full p-4 rounded-xl text-xs md:text-sm font-medium text-left border transition-all flex items-center justify-between ${
                          isSelected
                            ? 'bg-blue-50/80 border-blue-600 text-blue-700 shadow-xs ring-1 ring-blue-600 font-semibold'
                            : 'bg-white border-slate-200 text-slate-800 hover:bg-slate-50'
                        }`}
                      >
                        <span className="flex-1 pr-3">{opt}</span>
                        <div className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 ${
                          isSelected ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'
                        }`}>
                          {isSelected && <Check className="w-3 h-3" />}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Question Navigation & Submit */}
                <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                  <button
                    onClick={() => setCurrentQuestionIdx((p) => Math.max(0, p - 1))}
                    disabled={currentQuestionIdx === 0}
                    className="px-4 py-2 text-xs font-semibold rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-100 disabled:opacity-40"
                  >
                    Previous
                  </button>

                  {currentQuestionIdx < testQuestions.length - 1 ? (
                    <button
                      onClick={() => setCurrentQuestionIdx((p) => p + 1)}
                      className="px-5 py-2.5 text-xs font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:opacity-95 flex items-center gap-1.5 shadow-xs"
                    >
                      <span>Next Question</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSubmitTest}
                      disabled={submitMutation.isPending || selectedAnswers.includes(-1)}
                      className="px-6 py-2.5 text-xs font-bold rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition-all flex items-center gap-2 disabled:opacity-50 shadow-xs"
                    >
                      {submitMutation.isPending ? 'Scoring Answers...' : 'Submit 3-Min Test'}
                    </button>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
