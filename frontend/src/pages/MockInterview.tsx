import { useState, useEffect } from 'react';
import { 
  Play, 
  Send, 
  RotateCcw, 
  CheckCircle2, 
  AlertCircle, 
  Lightbulb, 
  Award, 
  Sparkles, 
  BookOpen, 
  ChevronRight, 
  HelpCircle, 
  Clock, 
  Layers, 
  Check, 
  Brain, 
  ShieldAlert, 
  Flame, 
  ArrowRight,
  X
} from 'lucide-react';
import { getModuleState, saveModuleState } from '../api/persistence';
import { interviewApi, type TrajectoryStep } from '../api/interview';

interface Evaluation {
  score: number;
  what_was_correct: string;
  what_was_missing: string;
  how_to_improve: string;
  ideal_answer: string;
  follow_up: string;
  detected_concept?: string;
  mastery_assessment?: string;
}

interface QuestionItem {
  id: number;
  question: string;
  category: string;
  key_concepts: string[];
  difficulty: string;
}

const ROLES = [
  'AI/ML Engineer',
  'Software Engineer',
  'Full Stack Developer',
  'Data Scientist',
  'Generative AI Engineer'
];

const DIFFICULTIES = ['Beginner', 'Intermediate', 'Advanced'];

const ROUNDS = [
  'Technical',
  'AI/ML',
  'Coding',
  'Project',
  'HR',
  'Full Interview'
];

const TOPICS = [
  'Java', 'Python', 'DSA', 'OOP', 'SQL', 'DBMS', 
  'System Design', 'AI/ML', 'RAG', 'LLMs', 'FastAPI', 'React'
];

export default function MockInterview() {
  const [restoreLoading, setRestoreLoading] = useState(true);

  // Config state
  const [role, setRole] = useState('AI/ML Engineer');
  const [difficulty, setDifficulty] = useState('Intermediate');
  const [interviewType, setInterviewType] = useState('Technical');
  const [useResume, setUseResume] = useState(true);
  const [enableAdaptive, setEnableAdaptive] = useState(true);

  // Active Session state
  const [isActive, setIsActive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [questionIndex, setQuestionIndex] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [userAnswer, setUserAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [historyScores, setHistoryScores] = useState<number[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isSaved, setIsSaved] = useState(false);

  // Feature 3: Adaptive Trajectory State
  const [adaptiveTrajectory, setAdaptiveTrajectory] = useState<TrajectoryStep[]>([]);
  const [adaptiveDecision, setAdaptiveDecision] = useState<string | null>(null);
  const [adaptiveReasoning, setAdaptiveReasoning] = useState<string | null>(null);
  const [cachedNextQuestion, setCachedNextQuestion] = useState<string | null>(null);

  // Feature 4: Technical Interrogation Chain State
  const [isInterrogationOpen, setIsInterrogationOpen] = useState(false);
  const [interrogationHistory, setInterrogationHistory] = useState<{ role: 'ai' | 'user'; text: string }[]>([]);
  const [interrogationInput, setInterrogationInput] = useState('');
  const [isInterrogating, setIsInterrogating] = useState(false);
  const [interrogationVerdict, setInterrogationVerdict] = useState<any | null>(null);

  // Quick Questions Bank state
  const [selectedTopic, setSelectedTopic] = useState('Java');
  const [topicQuestions, setTopicQuestions] = useState<QuestionItem[]>([]);
  const [isLoadingTopic, setIsLoadingTopic] = useState(false);

  // Restore state on mount from backend
  useEffect(() => {
    async function restoreState() {
      setRestoreLoading(true);
      const saved = await getModuleState('mock_interview');
      if (saved && typeof saved === 'object') {
        if (saved.role) setRole(saved.role);
        if (saved.difficulty) setDifficulty(saved.difficulty);
        if (saved.interview_type) setInterviewType(saved.interview_type);
        if (saved.use_resume !== undefined) setUseResume(saved.use_resume);
        if (saved.enable_adaptive !== undefined) setEnableAdaptive(saved.enable_adaptive);
        if (saved.is_active) {
          setIsActive(true);
          setSessionId(saved.session_id || '');
          setQuestionIndex(saved.question_index || 1);
          setTotalQuestions(saved.total_questions || 5);
          setCurrentQuestion(saved.current_question || '');
          setUserAnswer(saved.user_answer || '');
          setEvaluation(saved.evaluation || null);
          setHistoryScores(saved.history_scores || []);
          setIsCompleted(saved.is_completed || false);
          setAdaptiveTrajectory(saved.adaptive_trajectory || []);
          setAdaptiveDecision(saved.adaptive_decision || null);
          setAdaptiveReasoning(saved.adaptive_reasoning || null);
        }
      }
      setRestoreLoading(false);
    }
    restoreState();
  }, []);

  const saveInterviewState = async (overrides: Record<string, any> = {}) => {
    setIsSaved(false);
    const stateToSave = {
      role,
      difficulty,
      interview_type: interviewType,
      use_resume: useResume,
      enable_adaptive: enableAdaptive,
      is_active: isActive,
      session_id: sessionId,
      question_index: questionIndex,
      total_questions: totalQuestions,
      current_question: currentQuestion,
      user_answer: userAnswer,
      evaluation: evaluation,
      history_scores: historyScores,
      is_completed: isCompleted,
      adaptive_trajectory: adaptiveTrajectory,
      adaptive_decision: adaptiveDecision,
      adaptive_reasoning: adaptiveReasoning,
      ...overrides
    };
    await saveModuleState('mock_interview', stateToSave);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const startSession = async () => {
    setIsStarting(true);
    setErrorMessage('');
    setEvaluation(null);
    setUserAnswer('');
    setIsCompleted(false);
    setHistoryScores([]);
    setCachedNextQuestion(null);
    setIsInterrogationOpen(false);
    setInterrogationVerdict(null);
    setInterrogationHistory([]);

    try {
      const data = await interviewApi.start({
        role,
        difficulty,
        interview_type: interviewType,
        use_resume: useResume,
        enable_adaptive: enableAdaptive
      });

      setSessionId(data.session_id);
      setCurrentQuestion(data.question);
      setQuestionIndex(data.question_index);
      setTotalQuestions(data.total_questions);
      setIsActive(true);
      setAdaptiveTrajectory(data.adaptive_trajectory || [
        {
          step: 1,
          question: data.question,
          status: 'in_progress',
          adaptive_decision: 'Initial Diagnostic Question'
        }
      ]);
      setAdaptiveDecision(null);
      setAdaptiveReasoning(null);

      await saveInterviewState({
        is_active: true,
        session_id: data.session_id,
        current_question: data.question,
        question_index: data.question_index,
        total_questions: data.total_questions,
        is_completed: false,
        evaluation: null,
        user_answer: '',
        history_scores: [],
        adaptive_trajectory: data.adaptive_trajectory || []
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start interview.');
    } finally {
      setIsStarting(false);
    }
  };

  const submitAnswer = async () => {
    if (!userAnswer.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage('');

    try {
      const data = await interviewApi.evaluate({
        session_id: sessionId,
        role,
        difficulty,
        interview_type: interviewType,
        question: currentQuestion,
        answer: userAnswer.trim(),
        question_index: questionIndex,
        total_questions: totalQuestions,
        use_resume: useResume,
        enable_adaptive: enableAdaptive,
        previous_trajectory: adaptiveTrajectory
      });

      setEvaluation(data.evaluation);
      let newScores = historyScores;
      if (data.evaluation && typeof data.evaluation.score === 'number') {
        newScores = [...historyScores, data.evaluation.score];
        setHistoryScores(newScores);
      }

      if (data.is_complete) {
        setIsCompleted(true);
      }

      setCachedNextQuestion(data.next_question);
      setAdaptiveDecision(data.adaptive_decision || null);
      setAdaptiveReasoning(data.adaptive_reasoning || null);
      if (data.adaptive_trajectory) {
        setAdaptiveTrajectory(data.adaptive_trajectory);
      }

      await saveInterviewState({
        evaluation: data.evaluation,
        history_scores: newScores,
        is_completed: Boolean(data.is_complete),
        user_answer: userAnswer.trim(),
        adaptive_decision: data.adaptive_decision,
        adaptive_reasoning: data.adaptive_reasoning,
        adaptive_trajectory: data.adaptive_trajectory
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to evaluate answer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    if (questionIndex >= totalQuestions) {
      setIsCompleted(true);
      saveInterviewState({ is_completed: true });
      return;
    }

    const nextIdx = questionIndex + 1;
    setQuestionIndex(nextIdx);
    setEvaluation(null);
    setUserAnswer('');
    setIsInterrogationOpen(false);
    setInterrogationVerdict(null);
    setInterrogationHistory([]);

    if (cachedNextQuestion) {
      setCurrentQuestion(cachedNextQuestion);
      setCachedNextQuestion(null);
      saveInterviewState({
        question_index: nextIdx,
        current_question: cachedNextQuestion,
        evaluation: null,
        user_answer: '',
        is_completed: false
      });
    } else {
      fetchNextQuestion(nextIdx);
    }
  };

  const fetchNextQuestion = async (nextIdx: number) => {
    try {
      const data = await interviewApi.start({
        role,
        difficulty,
        interview_type: interviewType,
        use_resume: useResume,
        enable_adaptive: enableAdaptive
      });
      setCurrentQuestion(data.question);
      await saveInterviewState({
        question_index: nextIdx,
        current_question: data.question,
        evaluation: null,
        user_answer: '',
        is_completed: false
      });
    } catch (err) {
      console.warn("Could not dynamically fetch next question:", err);
    }
  };

  // Feature 4: Technical Interrogation Challenge Handlers
  const startInterrogation = async () => {
    setIsInterrogationOpen(true);
    setIsInterrogating(true);
    setInterrogationVerdict(null);

    try {
      const res = await interviewApi.interrogate({
        session_id: sessionId,
        role,
        question: currentQuestion,
        answer: userAnswer,
        interrogation_history: []
      });

      if (res.interrogation_question) {
        setInterrogationHistory([
          { role: 'ai', text: res.interrogation_question }
        ]);
      }
    } catch (err) {
      console.error('Failed to start interrogation:', err);
    } finally {
      setIsInterrogating(false);
    }
  };

  const sendInterrogationReply = async () => {
    if (!interrogationInput.trim() || isInterrogating) return;

    const userText = interrogationInput.trim();
    const updatedHistory: { role: 'ai' | 'user'; text: string }[] = [
      ...interrogationHistory,
      { role: 'user', text: userText }
    ];
    setInterrogationHistory(updatedHistory);
    setInterrogationInput('');
    setIsInterrogating(true);

    try {
      const res = await interviewApi.interrogate({
        session_id: sessionId,
        role,
        question: currentQuestion,
        answer: userAnswer,
        interrogation_history: updatedHistory
      });

      if (res.is_complete && res.defense_feedback) {
        setInterrogationVerdict(res.defense_feedback);
      } else if (res.interrogation_question) {
        setInterrogationHistory([
          ...updatedHistory,
          { role: 'ai', text: res.interrogation_question }
        ]);
      }
    } catch (err) {
      console.error('Failed to submit interrogation defense:', err);
    } finally {
      setIsInterrogating(false);
    }
  };

  const loadTopicQuestions = async (topic: string) => {
    setSelectedTopic(topic);
    setIsLoadingTopic(true);
    try {
      const data = await interviewApi.getQuestions(topic, difficulty, 5);
      setTopicQuestions(data.questions || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingTopic(false);
    }
  };

  const averageScore = historyScores.length > 0
    ? (historyScores.reduce((a, b) => a + b, 0) / historyScores.length).toFixed(1)
    : '0';

  if (restoreLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-muted-foreground">Restoring saved mock interview session...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto pb-12">
      {/* Top Banner */}
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-3">
            <Brain className="w-3.5 h-3.5" /> Adaptive Interview Engine & Interrogation Chain
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Adaptive Mock Interview Simulator</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Dynamically branches next questions based on previous answers, with technical interrogation follow-ups.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isSaved && (
            <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
              <Check className="w-3.5 h-3.5" /> Progress Saved
            </span>
          )}
          {isActive && (
            <button
              onClick={async () => {
                setIsActive(false);
                await saveInterviewState({ is_active: false });
              }}
              className="self-start md:self-auto px-4 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-slate-50 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 transition-colors flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" /> End Session
            </button>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Screen 1: Configuration & Setup */}
      {!isActive ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Config Form */}
          <div className="lg:col-span-2 space-y-6 p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-600" /> Session Settings
            </h2>

            {/* Target Role */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
                Target Role
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`p-3 rounded-xl text-xs font-medium text-left border transition-all ${
                      role === r 
                        ? 'border-blue-600 bg-blue-50/70 text-blue-700 shadow-xs ring-1 ring-blue-600 font-semibold' 
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Interview Round */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
                Interview Round / Focus
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {ROUNDS.map((rd) => (
                  <button
                    key={rd}
                    onClick={() => setInterviewType(rd)}
                    className={`p-3 rounded-xl text-xs font-medium text-left border transition-all ${
                      interviewType === rd 
                        ? 'border-blue-600 bg-blue-50/70 text-blue-700 shadow-xs ring-1 ring-blue-600 font-semibold' 
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {rd} Round
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
                Difficulty Level
              </label>
              <div className="flex gap-3">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d}
                    onClick={() => setDifficulty(d)}
                    className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-medium border text-center transition-all ${
                      difficulty === d
                        ? 'border-blue-600 bg-blue-50/70 text-blue-700 shadow-xs ring-1 ring-blue-600 font-semibold'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {/* Feature 3: Adaptive Engine Toggle */}
            <div className="pt-2 border-t border-slate-100 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer p-4 rounded-xl bg-blue-50/60 border border-blue-200/80">
                <input
                  type="checkbox"
                  checked={enableAdaptive}
                  onChange={(e) => setEnableAdaptive(e.target.checked)}
                  className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 accent-blue-600 mt-0.5"
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-900">
                      🧠 Enable Adaptive Interview Engine
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-600 text-white uppercase">
                      Recommended
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                    Instead of a static question list, the AI dynamically decides next questions based on your previous answers (e.g. good answer ➔ branch deeper, weak answer ➔ isolate the conceptual gap, compare strategies, or design the pipeline).
                  </p>
                </div>
              </label>

              {/* Resume Toggle */}
              <label className="flex items-center gap-3 cursor-pointer pl-1">
                <input
                  type="checkbox"
                  checked={useResume}
                  onChange={(e) => setUseResume(e.target.checked)}
                  className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 accent-blue-600"
                />
                <div>
                  <span className="text-xs font-medium text-slate-700">
                    Personalize with Uploaded Resume / Career Twin
                  </span>
                </div>
              </label>
            </div>

            {/* Launch Button */}
            <div className="pt-2">
              <button
                onClick={startSession}
                disabled={isStarting}
                className="w-full py-3.5 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:opacity-95 transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
              >
                {isStarting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Initializing Adaptive Engine & Diagnostic Q1...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Begin Adaptive Mock Interview ({role})
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick Technical Topic Questions Generator */}
          <div className="space-y-4 p-6 rounded-2xl border border-slate-200 bg-white shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2 text-slate-900 font-bold text-sm">
                <BookOpen className="w-4 h-4 text-blue-600" /> Topic Question Bank
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Explore top curated interview questions categorized by language or technology.
              </p>

              {/* Topic Pills */}
              <div className="flex flex-wrap gap-1.5 mb-4">
                {TOPICS.map((topic) => (
                  <button
                    key={topic}
                    onClick={() => loadTopicQuestions(topic)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors border ${
                      selectedTopic === topic
                        ? 'bg-blue-600 text-white border-blue-600 font-semibold'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {topic}
                  </button>
                ))}
              </div>

              {/* Topic Questions List */}
              <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                {isLoadingTopic ? (
                  <div className="py-8 text-center text-xs text-slate-400 animate-pulse">
                    Generating {selectedTopic} interview questions...
                  </div>
                ) : topicQuestions.length > 0 ? (
                  topicQuestions.map((q) => (
                    <div key={q.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50/60 text-xs space-y-1.5">
                      <div className="font-medium text-slate-800">{q.question}</div>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                        <span className="text-blue-600 font-medium">{q.category}</span>
                        <span>{q.difficulty}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs text-slate-400">
                    Click any topic pill above to load curated interview questions.
                  </div>
                )}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
              <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <span>Adaptive questions dynamically tailor to your real performance rubrics.</span>
            </div>
          </div>
        </div>
      ) : isCompleted ? (
        /* Screen 3: Completion & Scorecard Summary */
        <div className="p-8 md:p-10 rounded-2xl border border-slate-200 bg-white text-center max-w-2xl mx-auto space-y-6 shadow-xs">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center mx-auto">
            <Award className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Interview Session Completed!</h2>
            <p className="text-sm text-slate-500 mt-1">
              You completed the adaptive session for {role}.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 inline-block min-w-[240px]">
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Average Score</div>
            <div className="text-4xl font-extrabold text-blue-600 mt-1">{averageScore} / 10</div>
            <div className="text-xs text-slate-500 mt-1">Across {historyScores.length} evaluated questions</div>
          </div>

          {/* Adaptive Path Summary */}
          {adaptiveTrajectory.length > 0 && (
            <div className="text-left p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                Adaptive Trajectory History
              </span>
              <div className="space-y-1.5 text-xs text-slate-600">
                {adaptiveTrajectory.map((t, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="font-bold text-slate-800">Q{t.step}:</span>
                    <span>{t.question.slice(0, 75)}...</span>
                    {t.score && <span className="text-blue-600 font-semibold">({t.score}/10)</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-4 justify-center pt-2">
            <button
              onClick={() => setIsActive(false)}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold hover:opacity-95 transition-all text-sm shadow-xs"
            >
              Start Another Round
            </button>
          </div>
        </div>
      ) : (
        /* Screen 2: Active Adaptive Simulation */
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Progress Header */}
          <div className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                {role}
              </span>
              <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
                {interviewType}
              </span>
              {enableAdaptive && (
                <span className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-purple-50 text-purple-700 border border-purple-200 flex items-center gap-1">
                  <Brain className="w-3 h-3" /> Adaptive Engine Active
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <Clock className="w-3.5 h-3.5" />
              <span>Question {questionIndex} of {totalQuestions}</span>
            </div>
          </div>

          {/* Feature 3: Visual Adaptive Decision & Trajectory Tracker */}
          {enableAdaptive && (
            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5 text-blue-600" /> Adaptive Trajectory Chain
                </span>
                {adaptiveDecision && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    {adaptiveDecision}
                  </span>
                )}
              </div>

              {/* Trajectory Stepper */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {adaptiveTrajectory.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-1.5">
                    <div className={`px-2.5 py-1 rounded-lg border font-mono text-[11px] flex items-center gap-1.5 ${
                      step.status === 'completed'
                        ? (step.score || 0) >= 7
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : (step.score || 0) >= 5
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-blue-600 font-bold'
                    }`}>
                      <span>Q{step.step}</span>
                      {step.score && <span>({step.score}/10)</span>}
                    </div>
                    {idx < adaptiveTrajectory.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-slate-400" />
                    )}
                  </div>
                ))}
              </div>

              {adaptiveReasoning && (
                <div className="text-xs text-slate-700 pl-2 border-l-2 border-blue-600 mt-1">
                  <strong className="text-blue-700">AI Dynamic Rationale:</strong> {adaptiveReasoning}
                </div>
              )}
            </div>
          )}

          {/* Question Card */}
          <div className="p-6 md:p-8 rounded-2xl border border-blue-200/80 bg-gradient-to-br from-blue-50/40 via-white to-white shadow-xs space-y-3">
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-600 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Interviewer Prompt
            </div>
            <h2 className="text-lg md:text-xl font-bold text-slate-900 leading-snug">
              {currentQuestion}
            </h2>
          </div>

          {/* Candidate Answer Input */}
          {!evaluation && (
            <div className="space-y-4 p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Your Answer
                </label>
                <span className="text-xs text-slate-400">
                  {userAnswer.split(/\s+/).filter(Boolean).length} words
                </span>
              </div>

              <textarea
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                placeholder="Type your answer here. Be specific about tools, scale, and architectural decisions (e.g., 'We used Qdrant for vector search because...')"
                rows={7}
                className="w-full p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-y leading-relaxed transition-all"
              />

              <div className="flex justify-end pt-2">
                <button
                  onClick={submitAnswer}
                  disabled={!userAnswer.trim() || isSubmitting}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-sm hover:opacity-95 transition-all shadow-xs flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Evaluating & Deciding Adaptive Branch...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Submit Answer for Live Evaluation
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Structured Evaluation Card */}
          {evaluation && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-3 duration-500">
              <div className="p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs space-y-6">
                {/* Score & Verdict */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Interviewer Evaluation
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5">Performance Scorecard</h3>
                  </div>

                  <div className={`px-4 py-2 rounded-xl font-bold text-base border flex items-center gap-1.5 ${
                    evaluation.score >= 8 
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                      : evaluation.score >= 6 
                      ? 'bg-amber-50 text-amber-700 border-amber-200' 
                      : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    <Award className="w-4 h-4" />
                    Score: {evaluation.score} / 10
                  </div>
                </div>

                {/* What Was Correct */}
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-emerald-600 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> What You Did Well
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed pl-5">
                    {evaluation.what_was_correct || "No technical strengths demonstrated."}
                  </p>
                </div>

                {/* Drawbacks & What Was Missing */}
                <div className="space-y-1.5">
                  <div className={`text-xs font-semibold flex items-center gap-1.5 ${evaluation.score <= 4 ? 'text-rose-600' : 'text-amber-600'}`}>
                    <AlertCircle className="w-4 h-4" /> Drawbacks & Missing Technical Nuances
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed pl-5">
                    {evaluation.what_was_missing}
                  </p>
                </div>

                {/* How to Improve */}
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-blue-600 flex items-center gap-1.5">
                    <Lightbulb className="w-4 h-4" /> How to Articulate Better
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed pl-5">
                    {evaluation.how_to_improve}
                  </p>
                </div>

                {/* Perfect Model Answer */}
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="text-xs font-semibold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Perfect Model Answer (FAANG Standard)
                  </div>
                  <p className="text-xs md:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap font-sans bg-white p-4 rounded-xl border border-slate-200">
                    {evaluation.ideal_answer}
                  </p>
                </div>

                {/* Feature 4: Technical Interrogation Launcher Button */}
                <div className="p-4 md:p-5 rounded-xl bg-purple-50/70 border border-purple-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-bold uppercase tracking-wider text-purple-700 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-purple-600" /> 4. Technical Interrogation Follow-up Generator
                    </div>
                    <p className="text-xs text-slate-600">
                      Real interviewers challenge your choices (e.g. "Why Qdrant instead of SQL? What if 10M chunks? How to reduce latency?").
                    </p>
                  </div>
                  <button
                    onClick={startInterrogation}
                    className="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 shrink-0 shadow-xs"
                  >
                    <Flame className="w-3.5 h-3.5" /> Challenge My Answer
                  </button>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 flex justify-end">
                  <button
                    onClick={handleNextQuestion}
                    className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-sm hover:opacity-95 transition-all shadow-xs flex items-center gap-2"
                  >
                    <span>{questionIndex >= totalQuestions ? 'View Final Scorecard' : 'Next Adaptive Question'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feature 4: Interactive Interrogation Suite Modal */}
          {isInterrogationOpen && (
            <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
              <div className="w-full max-w-2xl bg-white border border-slate-200 rounded-2xl p-6 md:p-8 shadow-xl relative space-y-6 max-h-[90vh] flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
                      <Flame className="w-5 h-5 text-purple-600" /> Technical Interrogation Chain
                    </div>
                    <button
                      onClick={() => setIsInterrogationOpen(false)}
                      className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <p className="text-xs text-slate-500 mt-2">
                    The interviewer is grilling your specific technical choices. Defend your architecture under progressive pressure!
                  </p>
                </div>

                {/* Dialog History */}
                <div className="flex-1 overflow-y-auto space-y-4 max-h-[400px] pr-2">
                  {interrogationHistory.map((item, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-xl text-xs leading-relaxed ${
                        item.role === 'ai'
                          ? 'bg-purple-50 border border-purple-200 text-slate-800 mr-8'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white ml-8 shadow-xs'
                      }`}
                    >
                      <div className="font-semibold text-[11px] mb-1 opacity-80">
                        {item.role === 'ai' ? 'Senior Technical Interviewer' : 'You (Candidate)'}
                      </div>
                      <div>{item.text}</div>
                    </div>
                  ))}

                  {isInterrogating && (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      Interviewer formulating follow-up technical challenge...
                    </div>
                  )}

                  {interrogationVerdict && (
                    <div className="p-5 rounded-xl bg-emerald-50 border border-emerald-200 text-left space-y-2 mt-4 animate-in zoom-in-95">
                      <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider flex items-center gap-1.5">
                        <Award className="w-4 h-4 text-emerald-600" /> {interrogationVerdict.verdict_title}
                      </div>
                      <p className="text-xs text-slate-800">{interrogationVerdict.summary}</p>
                      <div className="text-[11px] text-slate-600 pt-1 border-t border-emerald-200">
                        <strong className="text-slate-900">Interviewer Evaluation Notes:</strong> {interrogationVerdict.interviewer_notes}
                      </div>
                    </div>
                  )}
                </div>

                {/* Input Area */}
                {!interrogationVerdict ? (
                  <div className="space-y-3 pt-2 border-t border-slate-100">
                    <textarea
                      value={interrogationInput}
                      onChange={(e) => setInterrogationInput(e.target.value)}
                      placeholder="Defend your decision: Address the scale limits, latency, and why alternative solutions were rejected..."
                      rows={3}
                      className="w-full p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 resize-none transition-all"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setIsInterrogationOpen(false)}
                        className="px-4 py-2 text-xs font-semibold rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
                      >
                        Exit Drill
                      </button>
                      <button
                        onClick={sendInterrogationReply}
                        disabled={!interrogationInput.trim() || isInterrogating}
                        className="px-5 py-2 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white flex items-center gap-1.5 disabled:opacity-50 shadow-xs transition-colors"
                      >
                        <Send className="w-3 h-3" /> Defend Technical Choice
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="pt-2 border-t border-slate-100 flex justify-end">
                    <button
                      onClick={() => setIsInterrogationOpen(false)}
                      className="px-5 py-2.5 text-xs font-bold rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-xs"
                    >
                      Done & Return to Evaluation
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
