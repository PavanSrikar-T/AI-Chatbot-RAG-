import { fetchApi } from './client';

export interface JobAnalysisRequest {
  job_description: string;
  resume_document_id?: string;
  days_until_interview?: number;
}

export interface LearningPhase {
  phase: string;
  timeframe: string;
  title: string;
  summary: string;
  daily_milestones: string[];
  recommended_resources: string[];
}

export interface DSATopicItem {
  category: string;
  frequency: string;
  importance: string;
  target_problems: string[];
  core_concept: string;
}

export interface PrepInterviewQuestion {
  question: string;
  category: string;
  why_asked: string;
  sample_answer_hint: string;
}

export interface BulletRewrite {
  original: string;
  optimized: string;
  reason: string;
}

export interface ResumeAlignmentData {
  target_role: string;
  estimated_ats_score: number;
  missing_keywords: string[];
  bullet_rewrites: BulletRewrite[];
  ats_recommendations: string[];
}

export interface JobAnalysisResponse {
  required_skills: string[];
  skill_gap: string[];
  match_score: number;
  recommendations: string;
  // Feature 2 fields
  target_role?: string;
  match_skills?: string[];
  partial_skills?: string[];
  gap_skills?: string[];
  days_until_interview?: number;
  learning_plan?: LearningPhase[];
  dsa_plan?: DSATopicItem[];
  interview_questions?: PrepInterviewQuestion[];
  resume_alignment?: ResumeAlignmentData;
}

export const jobsApi = {
  analyzeJob: (data: JobAnalysisRequest): Promise<JobAnalysisResponse> => {
    return fetchApi('/jobs/analyze', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getLatestAnalysis: (): Promise<JobAnalysisResponse | null> => {
    return fetchApi('/jobs/latest', {
      method: 'GET',
    });
  }
};
