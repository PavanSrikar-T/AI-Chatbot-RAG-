import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import DashboardLayout from './components/layout/DashboardLayout';

const queryClient = new QueryClient();
import LandingPage from './pages/LandingPage';
import KnowledgeBase from './pages/KnowledgeBase';
import AIChat from './pages/AIChat';
import JobAnalyzer from './pages/JobAnalyzer';
import MockInterview from './pages/MockInterview';
import InterviewReadiness from './pages/InterviewReadiness';
import SkillRetention from './pages/SkillRetention';

import { profileApi } from './api/profile';
import { interviewApi } from './api/interview';
import { retentionApi } from './api/retention';
import { 
  BarChart3, 
  Clock, 
  ChevronRight, 
  Sparkles, 
  Briefcase, 
  GraduationCap, 
  FileText, 
  Brain, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Award,
  Layers,
  ArrowUpRight
} from 'lucide-react';

function DashboardHome() {
  const navigate = useNavigate();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: profileApi.getDashboardStats,
    refetchOnWindowFocus: true,
  });

  const { data: heatmapData } = useQuery({
    queryKey: ['readiness-heatmap'],
    queryFn: interviewApi.getReadinessHeatmap,
  });

  const { data: retentionData } = useQuery({
    queryKey: ['skill-retention-status'],
    queryFn: retentionApi.getStatus,
  });

  const userName = stats?.user_name || 'Pavan';
  const jobMatchesCount = stats?.job_matches_count ?? 1;
  const readiness = stats?.interview_readiness || '78%';
  const documentsCount = stats?.documents_count ?? 2;
  const latestAnalysis = stats?.latest_job_analysis;

  const retentionPrompt = retentionData?.prompt_notification;
  const domains = heatmapData?.domains || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto pb-12">
      {/* Welcome Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            {isLoading ? 'Welcome back' : `Good morning, ${userName} 👋`}
          </h1>
          <p className="text-slate-500 mt-1 text-sm md:text-base">
            Here's your current career preparation progress across all live AI evaluation modules.
          </p>
        </div>

        {/* Quick Top Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/interview')}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-all shadow-sm shadow-blue-500/20 flex items-center gap-2"
          >
            <GraduationCap className="w-4 h-4" /> Start Mock Interview
          </button>
          <button
            onClick={() => navigate('/jobs')}
            className="px-4 py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors shadow-xs flex items-center gap-2"
          >
            <Briefcase className="w-4 h-4 text-slate-500" /> Match Job Description
          </button>
        </div>
      </div>

      {/* Feature 6: Skill Decay Alert Banner (Light Professional Theme) */}
      {retentionPrompt && (
        <div 
          onClick={() => navigate('/retention')}
          className="p-5 rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 via-white to-amber-50/50 flex items-center justify-between gap-4 cursor-pointer hover:border-amber-300 transition-all shadow-xs group"
        >
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" /> Memory Decay Alert: Practice Needed
              </div>
              <h3 className="text-sm font-semibold text-slate-800 mt-0.5">{retentionPrompt.message}</h3>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-700 group-hover:translate-x-1 transition-transform shrink-0">
            <span>Take 3-Min Test</span>
            <ChevronRight className="w-4 h-4" />
          </div>
        </div>
      )}

      {/* Grid Row 1: Career Readiness Scorecard + Career Digital Twin Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Career Readiness Hero Card */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-3xl p-6 md:p-8 shadow-card space-y-6">
          <div className="flex items-start justify-between pb-4 border-b border-slate-100">
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-600 mb-1">
                <BarChart3 className="w-4 h-4" /> Comprehensive Evaluation
              </div>
              <h2 className="text-2xl font-bold text-slate-900">Career Readiness Score</h2>
              <p className="text-xs text-slate-500 mt-0.5">Weighted composite based on mock interviews, DSA problem solving, and project defense</p>
            </div>

            <div className="text-right">
              <div className="text-4xl font-black text-blue-600 font-mono">
                {readiness}
              </div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Target Role: AI/ML</span>
            </div>
          </div>

          {/* Sub-Metrics Progress Bars */}
          <div className="space-y-4">
            {[
              { label: 'Technical Core', score: 84, color: 'bg-blue-600' },
              { label: 'Data Structures & Algorithms (DSA)', score: 61, color: 'bg-amber-500' },
              { label: 'AI/ML & RAG Architecture', score: 88, color: 'bg-purple-600' },
              { label: 'Project Verification & Ownership', score: 84, color: 'bg-emerald-600' },
              { label: 'Communication & STAR Stories', score: 73, color: 'bg-sky-600' },
            ].map((metric, i) => (
              <div key={i} className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-medium text-slate-700">{metric.label}</span>
                  <span className="font-bold font-mono text-slate-900">{metric.score}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-700 ${metric.color}`}
                    style={{ width: `${metric.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100">
            <span>Calibrated against FAANG & top tech rubrics</span>
            <button
              onClick={() => navigate('/readiness')}
              className="text-blue-600 font-semibold hover:underline flex items-center gap-1"
            >
              <span>Explore Detailed Weakness Heatmap</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Career Digital Twin Card */}
        <div className="lg:col-span-5 bg-gradient-to-br from-indigo-50/50 via-white to-purple-50/30 border border-slate-200 rounded-3xl p-6 md:p-8 shadow-card flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-2.5 py-0.5 rounded-full">
                <Brain className="w-3.5 h-3.5 text-indigo-600" /> Career Digital Twin
              </div>
              <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full">
                Live Synced
              </span>
            </div>

            <h3 className="text-xl font-bold text-slate-900">Your AI-Generated Career Profile</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Synthesized from your indexed documents, projects, and interview responses.
            </p>

            {/* Small Icon Grid */}
            <div className="grid grid-cols-2 gap-3 mt-5">
              {[
                { icon: Layers, title: 'Verified Skills', desc: '18 Skills Indexed', color: 'text-blue-600 bg-blue-50' },
                { icon: Briefcase, title: 'Job Matches', desc: `${jobMatchesCount} Analyzed Roles`, color: 'text-purple-600 bg-purple-50' },
                { icon: FileText, title: 'Knowledge Base', desc: `${documentsCount} Resumes Uploaded`, color: 'text-sky-600 bg-sky-50' },
                { icon: Award, title: 'Evaluation Level', desc: 'Mid-Senior Level', color: 'text-emerald-600 bg-emerald-50' },
              ].map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div key={idx} className="p-3 rounded-2xl bg-white border border-slate-200/90 shadow-2xs space-y-1">
                    <div className={`w-7 h-7 rounded-lg ${item.color} flex items-center justify-center`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="text-xs font-bold text-slate-800">{item.title}</div>
                    <div className="text-[11px] text-slate-500">{item.desc}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={() => navigate('/documents')}
              className="w-full py-3 px-4 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 font-semibold text-xs text-slate-700 shadow-xs flex items-center justify-center gap-1.5 group transition-colors"
            >
              <span>View Career Digital Twin & Documents</span>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-slate-700 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </button>
          </div>
        </div>
      </div>

      {/* Grid Row 2: Weakness Heatmap At A Glance */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 shadow-card space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-blue-600 flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4" /> Domain Readiness Breakdown
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5">Interview Weakness Heatmap</h2>
            <p className="text-xs text-slate-500">Click any domain to inspect sub-criteria rubrics and understand why the score was assigned.</p>
          </div>

          <button
            onClick={() => navigate('/readiness')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>Full Heatmap View</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* 8 Domain Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {domains.slice(0, 8).map((dom) => {
            const isReady = dom.score >= 80;
            const isModerate = dom.score >= 65;
            return (
              <div
                key={dom.id}
                onClick={() => navigate('/readiness')}
                className="p-4 rounded-2xl bg-slate-50/70 border border-slate-200 hover:border-blue-400 hover:bg-white hover:shadow-card transition-all cursor-pointer space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-blue-600 transition-colors">
                    {dom.name}
                  </span>
                  <span className={`text-xs font-mono font-bold ${
                    isReady ? 'text-emerald-600' : isModerate ? 'text-amber-600' : 'text-rose-600'
                  }`}>
                    {dom.score}%
                  </span>
                </div>

                <div className="w-full bg-slate-200/80 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      isReady ? 'bg-emerald-500' : isModerate ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${dom.score}%` }}
                  />
                </div>

                <p className="text-[10px] text-slate-500 line-clamp-1">
                  {dom.why_explanation}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid Row 3: Latest Job Match Summary Card */}
      {latestAnalysis && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 shadow-card space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-600 flex items-center gap-1.5">
                <Briefcase className="w-4 h-4" /> Latest Job Match Evaluation
              </div>
              <h2 className="text-xl font-bold text-slate-900 mt-0.5">
                Target Role: {latestAnalysis.target_role || 'AI/ML Engineer'}
              </h2>
              <p className="text-xs text-slate-500">Compared against your Career Digital Twin profile</p>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-3xl font-extrabold text-emerald-600 font-mono">
                  {latestAnalysis.match_score}%
                </div>
                <div className="text-[10px] font-semibold text-slate-400 uppercase">Match Score</div>
              </div>
              <button
                onClick={() => navigate('/jobs')}
                className="px-4 py-2 rounded-xl bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold text-xs border border-blue-200 transition-colors"
              >
                View 21-Day Plan
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 space-y-2">
              <div className="text-xs font-bold text-emerald-700 flex items-center gap-1.5 uppercase">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> MATCH (Verified Skills)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(latestAnalysis.match_skills || latestAnalysis.required_skills?.slice(0, 4) || []).map((s: string, idx: number) => (
                  <span key={idx} className="px-2.5 py-0.5 bg-white text-emerald-800 text-xs font-medium rounded-lg border border-emerald-200 shadow-2xs">
                    ✓ {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200/80 space-y-2">
              <div className="text-xs font-bold text-amber-700 flex items-center gap-1.5 uppercase">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> PARTIAL (Needs Polish)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(latestAnalysis.partial_skills || ['Transformers']).map((s: string, idx: number) => (
                  <span key={idx} className="px-2.5 py-0.5 bg-white text-amber-800 text-xs font-medium rounded-lg border border-amber-200 shadow-2xs">
                    ⚠ {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-rose-50/60 border border-rose-200/80 space-y-2">
              <div className="text-xs font-bold text-rose-700 flex items-center gap-1.5 uppercase">
                <XCircle className="w-3.5 h-3.5 text-rose-600" /> GAP (21-Day Focus)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(latestAnalysis.gap_skills || latestAnalysis.skill_gap?.slice(0, 4) || []).map((s: string, idx: number) => (
                  <span key={idx} className="px-2.5 py-0.5 bg-white text-rose-800 text-xs font-medium rounded-lg border border-rose-200 shadow-2xs">
                    ❌ {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid Row 4: Main Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-card hover:shadow-card-hover transition-all flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <GraduationCap className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Adaptive Mock Interview</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Practice multi-round technical and behavioral simulations. The AI dynamically adapts question depth to your answers.
            </p>
          </div>
          <button
            onClick={() => navigate('/interview')}
            className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            Launch Interview
          </button>
        </div>

        <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-card hover:shadow-card-hover transition-all flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Briefcase className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Job Description Analysis</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Paste target job requirements to generate a complete 21-day learning plan, role-specific DSA questions, and ATS resume optimizer.
            </p>
          </div>
          <button
            onClick={() => navigate('/jobs')}
            className="w-full py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors shadow-xs"
          >
            Analyze Job Spec
          </button>
        </div>

        <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-card hover:shadow-card-hover transition-all flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Brain className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Skill Retention Engine</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Track Ebbinghaus memory decay curves for learned frameworks and take 3-minute rapid tests to schedule needed revisions.
            </p>
          </div>
          <button
            onClick={() => navigate('/retention')}
            className="w-full py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors shadow-xs"
          >
            Open Retention Hub
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/*" element={
            <DashboardLayout>
              <Routes>
                <Route path="/" element={<DashboardHome />} />
                <Route path="/documents" element={<KnowledgeBase />} />
                <Route path="/chat" element={<AIChat />} />
                <Route path="/jobs" element={<JobAnalyzer />} />
                <Route path="/interview" element={<MockInterview />} />
                <Route path="/readiness" element={<InterviewReadiness />} />
                <Route path="/retention" element={<SkillRetention />} />
              </Routes>
            </DashboardLayout>
          } />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
