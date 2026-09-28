import { fetchApi } from './client';
import type { JobAnalysisResponse } from './jobs';

export interface DashboardStatsResponse {
  user_name: string;
  job_matches_count: number;
  interview_readiness: string;
  documents_count: number;
  latest_job_analysis?: JobAnalysisResponse;
}

export const profileApi = {
  getDashboardStats: (): Promise<DashboardStatsResponse> => {
    return fetchApi('/profile/dashboard-stats', {
      method: 'GET',
    });
  }
};
