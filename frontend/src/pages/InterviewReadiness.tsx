import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
  BarChart3, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  TrendingUp, 
  Play, 
  ChevronRight,
  Flame,
  Layers
} from 'lucide-react';
import { interviewApi, type ReadinessDomain } from '../api/interview';

export default function InterviewReadiness() {
  const navigate = useNavigate();
  const [selectedDomain, setSelectedDomain] = useState<ReadinessDomain | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['readiness-heatmap'],
    queryFn: interviewApi.getReadinessHeatmap,
  });

  const domains = data?.domains || [];
  const activeDomain = selectedDomain || domains[4] || domains[0]; // Default to System Design or first

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-500';
    if (score >= 65) return 'text-amber-500';
    return 'text-rose-500';
  };

  const getProgressBg = (score: number) => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 65) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const getBadgeStyle = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'needs_practice':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'critical_gap':
      default:
        return 'bg-rose-500/10 text-rose-500 border-rose-500/20';
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-3">
            <BarChart3 className="w-3.5 h-3.5" /> Technical Diagnosis & Rubric Breakdown
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Interview Weakness Heatmap</h1>
          <p className="text-slate-500 mt-1 text-sm max-w-2xl">
            Live multi-dimensional readiness scorecard calibrated across 8 technical domains. Explains explicitly <strong className="text-slate-900">WHY</strong> each score was assigned based on evaluated interview answers.
          </p>
        </div>

        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200 p-4 rounded-xl shadow-xs">
          <div className="text-right">
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Overall Readiness</div>
            <div className={`text-3xl font-extrabold ${getScoreColor(data?.overall_readiness || 73)}`}>
              {data?.overall_readiness || 73}%
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 shadow-xs">
            <Flame className="w-6 h-6" />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-500">Synthesizing live weakness heatmap...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Heatmap List (Left Column) */}
          <div className="lg:col-span-6 space-y-4">
            <div className="flex items-center justify-between px-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Domain Readiness Heatmap (Click to Inspect Rubric)
              </h2>
              <span className="text-xs text-slate-500">{domains.length} Evaluated Domains</span>
            </div>

            <div className="space-y-3">
              {domains.map((dom) => {
                const isSelected = activeDomain?.id === dom.id;
                const percentage = dom.score;
                const filledBlocks = Math.round(percentage / 10);
                const emptyBlocks = 10 - filledBlocks;
                const blockBar = '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);

                return (
                  <div
                    key={dom.id}
                    onClick={() => setSelectedDomain(dom)}
                    className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-white border-blue-600 ring-1 ring-blue-600 shadow-md'
                        : 'bg-white border-slate-200 hover:bg-slate-50 shadow-xs'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-slate-900 text-base w-32">{dom.name}</span>
                        <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${getBadgeStyle(dom.status)}`}>
                          {dom.status === 'ready' ? 'Ready' : dom.status === 'needs_practice' ? 'Needs Practice' : 'Critical Gap'}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-slate-400 hidden sm:inline">{blockBar}</span>
                        <span className={`text-base font-bold font-mono ${getScoreColor(dom.score)}`}>
                          {dom.score}%
                        </span>
                        <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? 'text-blue-600 translate-x-1' : 'text-slate-400'}`} />
                      </div>
                    </div>

                    {/* Visual Progress Bar */}
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${getProgressBg(dom.score)}`}
                        style={{ width: `${dom.score}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Drill-down Detail Panel (Right Column: Explaining WHY the score exists) */}
          {activeDomain && (
            <div className="lg:col-span-6 space-y-6 animate-in slide-in-from-right-4 duration-300">
              <div className="p-6 md:p-8 rounded-2xl border border-slate-200 bg-white shadow-xs space-y-6">
                {/* Domain Header */}
                <div className="flex items-start justify-between pb-6 border-b border-slate-100">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-blue-600 flex items-center gap-1.5 mb-1">
                      <Layers className="w-3.5 h-3.5" /> Rubric Evaluation Analysis
                    </div>
                    <h2 className="text-xl md:text-2xl font-bold text-slate-900">{activeDomain.name} Readiness: {activeDomain.score}%</h2>
                    <p className="text-xs text-slate-500 mt-1">
                      Based on <strong className="text-slate-800">{activeDomain.evaluated_answers_count} evaluated answers</strong> in technical sessions
                    </p>
                  </div>
                  <div className={`text-3xl font-extrabold ${getScoreColor(activeDomain.score)}`}>
                    {activeDomain.score}%
                  </div>
                </div>

                {/* Sub-Criteria Breakdown with /10 scores */}
                <div className="space-y-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
                    <span>Evaluated Sub-Criteria</span>
                    <span>Score (out of 10)</span>
                  </div>

                  <div className="space-y-2.5">
                    {activeDomain.criteria.map((crit, idx) => (
                      <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                        <div className="flex justify-between items-center text-xs font-medium mb-1.5">
                          <span className="text-slate-800 font-semibold">{crit.name}</span>
                          <span className="font-bold text-blue-600 font-mono">{crit.score} / {crit.max_score}</span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              crit.score >= 8 ? 'bg-emerald-500' : crit.score >= 6 ? 'bg-amber-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${(crit.score / crit.max_score) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Detailed Diagnosis: WHY THE SCORE EXISTS */}
                <div className="p-5 rounded-xl bg-blue-50/50 border border-blue-200/80 space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                    <HelpCircle className="w-3.5 h-3.5 text-blue-600" /> Why This Score Exists
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {activeDomain.why_explanation}
                  </p>
                </div>

                {/* Strengths & Weaknesses Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                    <div className="text-xs font-bold text-emerald-700 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Demonstrated Strengths
                    </div>
                    <ul className="text-xs text-slate-700 space-y-1">
                      {activeDomain.top_strengths.map((str, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                          <span>{str}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200 space-y-2">
                    <div className="text-xs font-bold text-rose-700 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" /> High-Priority Vulnerabilities
                    </div>
                    <ul className="text-xs text-slate-700 space-y-1">
                      {activeDomain.critical_weaknesses.map((weak, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
                          <span>{weak}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Recommended Immediate Drill */}
                <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                  <div className="text-xs space-y-1">
                    <div className="font-bold text-blue-700 uppercase tracking-wider">Targeted Remediation Drill</div>
                    <div className="text-slate-700 leading-relaxed">{activeDomain.recommended_drill}</div>
                  </div>
                </div>

                {/* Action CTA */}
                <div className="pt-2">
                  <button
                    onClick={() => navigate('/interview')}
                    className="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:opacity-95 transition-all shadow-xs flex items-center justify-center gap-2 text-sm"
                  >
                    <Play className="w-4 h-4 fill-current" /> Practice {activeDomain.name} Weakness in Mock Interview
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
