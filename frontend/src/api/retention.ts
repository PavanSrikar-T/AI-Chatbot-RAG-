import { fetchApi } from './client';

export interface RetentionSkill {
  skill: string;
  category: string;
  last_practiced: string;
  days_elapsed: number;
  current_retention: number;
  decay_status: 'fresh' | 'degrading' | 'critical';
  status_label: string;
  color: string;
  needs_test: boolean;
  revision_scheduled?: string | null;
}

export interface RetentionPromptNotification {
  skill: string;
  last_practiced: string;
  days_ago: number;
  retention: number;
  message: string;
}

export interface RetentionOverviewResponse {
  overall_retention: number;
  skills: RetentionSkill[];
  prompt_notification?: RetentionPromptNotification | null;
}

export interface TestQuestion {
  id: number;
  question: string;
  options: string[];
  correct_option_index: number;
  explanation: string;
}

export interface RetentionTestResponse {
  skill: string;
  time_limit_seconds: number;
  questions: TestQuestion[];
}

export interface SubmitRetentionTestResponse {
  skill: string;
  score_percentage: number;
  old_retention: number;
  new_retention: number;
  revision_scheduled: string | null;
  feedback: string;
  targeted_revision_questions: string[];
}

export const retentionApi = {
  getStatus: (): Promise<RetentionOverviewResponse> => {
    return fetchApi('/retention/status', {
      method: 'GET',
    });
  },

  startTest: (skill: string): Promise<RetentionTestResponse> => {
    return fetchApi('/retention/test', {
      method: 'POST',
      body: JSON.stringify({ skill }),
    });
  },

  submitTest: (skill: string, answers: number[]): Promise<SubmitRetentionTestResponse> => {
    return fetchApi('/retention/evaluate', {
      method: 'POST',
      body: JSON.stringify({ skill, answers }),
    });
  }
};
