import { ArrowRight, Brain, Zap, Target, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 overflow-hidden selection:bg-blue-100">
      {/* Navigation */}
      <nav className="container mx-auto px-6 py-5 flex items-center justify-between z-50 relative border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
            <Brain className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">CareerMind AI</span>
        </div>
        <div className="hidden md:flex space-x-8 text-sm font-medium text-slate-600">
          <a href="#features" className="hover:text-blue-600 transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-blue-600 transition-colors">How it Works</a>
          <a href="#testimonials" className="hover:text-blue-600 transition-colors">Testimonials</a>
        </div>
        <div className="flex items-center space-x-3">
          <Link to="/login" className="px-4 py-2 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">Log In</Link>
          <Link to="/register" className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:opacity-95 shadow-xs transition-all">Get Started</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative pt-16 pb-28 lg:pt-24 lg:pb-36">
        <div className="absolute inset-0 top-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-100/60 via-[#F8FAFC] to-[#F8FAFC]" />
        <div className="container mx-auto px-6 text-center">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-700 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <span className="flex h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
            <span>CareerMind AI 2.0 is now live</span>
          </div>
          <h1 className="text-4xl lg:text-6xl font-extrabold tracking-tight mb-6 leading-tight text-slate-900 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
            Your Intelligent <br className="hidden lg:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600">Career Copilot</span>
          </h1>
          <p className="max-w-2xl mx-auto text-base lg:text-lg text-slate-600 mb-10 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
            Advanced RAG-powered intelligence that analyzes your resume, matches you with jobs, builds complete 21-day roadmaps, and conducts hyper-realistic technical interviews.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-3 sm:space-y-0 sm:space-x-4 animate-in fade-in slide-in-from-bottom-10 duration-700 delay-300">
            <Link to="/register" className="w-full sm:w-auto px-7 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:opacity-95 shadow-sm transition-all flex items-center justify-center text-sm">
              Start Free Trial <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
            <a href="#features" className="w-full sm:w-auto px-7 py-3.5 bg-white text-slate-700 font-semibold rounded-xl hover:bg-slate-50 border border-slate-200 transition-all flex items-center justify-center text-sm shadow-xs">
              View Features
            </a>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="container mx-auto px-6 mt-24" id="features">
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Zap, title: "Smart Resume Analysis", desc: "Upload your PDF. We instantly extract skills, experience, and parse your technical gaps with grounded RAG." },
              { icon: Target, title: "Precision Job Matching", desc: "Compare your extracted profile against any job description for 21-day prep plans, ATS scores, and DSA roadmaps." },
              { icon: Shield, title: "Adaptive Mock Simulator", desc: "Face realistic technical questions dynamically generated from your resume and live answers with interrogation drills." }
            ].map((f, i) => (
              <div key={i} className="p-8 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-md transition-all duration-300 group">
                <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-6 border border-blue-100 group-hover:scale-105 transition-all">
                  <f.icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">{f.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

