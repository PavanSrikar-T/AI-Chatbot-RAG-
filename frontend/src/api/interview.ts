import { fetchApi } from './client';

export interface TrajectoryStep {
  step: number;
  question: string;
  score?: number;
  performance?: string;
  detected_mastery?: string;
  adaptive_decision?: string;
  adaptive_reasoning?: string;
  status: 'in_progress' | 'completed';
}

export interface StartInterviewRequest {
  role: string;
  difficulty: string;
  interview_type: string;
  use_resume: boolean;
  enable_adaptive?: boolean;
}

export interface StartInterviewResponse {
  session_id: string;
  role: string;
  difficulty: string;
  interview_type: string;
  question_index: number;
  total_questions: number;
  question: string;
  personalized: boolean;
  enable_adaptive: boolean;
  adaptive_trajectory?: TrajectoryStep[];
}

export interface EvaluationData {
  score: number;
  what_was_correct: string;
  what_was_missing: string;
  how_to_improve: string;
  ideal_answer: string;
  follow_up: string;
  detected_concept?: string;
  mastery_assessment?: string;
}

export interface EvaluateAnswerRequest {
  session_id: string;
  role: string;
  difficulty: string;
  interview_type: string;
  question: string;
  answer: string;
  question_index: number;
  total_questions: number;
  use_resume: boolean;
  enable_adaptive?: boolean;
  previous_trajectory?: TrajectoryStep[];
}

export interface EvaluateAnswerResponse {
  session_id: string;
  question_index: number;
  total_questions: number;
  is_complete: boolean;
  evaluation: EvaluationData;
  next_question: string | null;
  adaptive_decision?: string;
  adaptive_reasoning?: string;
  detected_mastery?: string;
  adaptive_trajectory?: TrajectoryStep[];
}

export interface InterrogationTurn {
  role: 'ai' | 'user';
  text: string;
}

export interface InterrogateRequest {
  session_id: string;
  role: string;
  question: string;
  answer: string;
  interrogation_history: InterrogationTurn[];
}

export interface InterrogateResponse {
  session_id: string;
  turn: number;
  is_complete: boolean;
  interrogation_question?: string;
  focus_topic: string;
  defense_feedback?: {
    score: number;
    verdict_title: string;
    summary: string;
    interviewer_notes: string;
  };
}

export interface ReadinessCriteria {
  name: string;
  score: number;
  max_score: number;
}

export interface ReadinessDomain {
  id: string;
  name: string;
  score: number;
  evaluated_answers_count: number;
  status: 'ready' | 'needs_practice' | 'critical_gap';
  criteria: ReadinessCriteria[];
  why_explanation: string;
  top_strengths: string[];
  critical_weaknesses: string[];
  recommended_drill: string;
}

export interface ReadinessHeatmapResponse {
  overall_readiness: number;
  domains: ReadinessDomain[];
  summary_verdict: string;
}

export const interviewApi = {
  start: (data: StartInterviewRequest): Promise<StartInterviewResponse> => {
    return fetchApi('/interview/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  evaluate: (data: EvaluateAnswerRequest): Promise<EvaluateAnswerResponse> => {
    return fetchApi('/interview/evaluate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  interrogate: (data: InterrogateRequest): Promise<InterrogateResponse> => {
    return fetchApi('/interview/interrogate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getReadinessHeatmap: (): Promise<ReadinessHeatmapResponse> => {
    return fetchApi('/interview/readiness-heatmap', {
      method: 'GET',
    });
  },

  getQuestions: (topic: string, difficulty: string, count: number = 5) => {
    return fetchApi('/interview/questions', {
      method: 'POST',
      body: JSON.stringify({ topic, difficulty, count }),
    });
  }
};
