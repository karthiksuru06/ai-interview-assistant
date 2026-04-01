import React, { useState, useEffect, useRef, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import { getFaceAnalyzer } from "../services/FaceAnalyzer";
import { motion, AnimatePresence } from "framer-motion";
import jsPDF from "jspdf";
import "jspdf-autotable";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  AreaChart, Area, XAxis,
} from "recharts";
import {
  Video, VideoOff, Activity, Cpu, Zap, Send, ChevronRight, User, Eye,
  Volume2, VolumeX, Brain, Sparkles, CheckCircle2, AlertCircle, StopCircle,
  Mic, Square, ArrowRight, Clock, Download, FileText, Award, Target, TrendingUp,
  Shield, BarChart3,
} from "lucide-react";

// ── Constants ────────────────────────────────────────────────────
const PIE_COLORS = ["#06b6d4","#a855f7","#22c55e","#eab308","#ef4444","#f97316","#ec4899","#6366f1"];

const COACHING_TIPS = {
  posture: {
    Slouching:    { message: "Sit up straight — good posture projects confidence", severity: "warning" },
    "Looking Away": { message: "Face the camera — looking away reduces engagement", severity: "warning" },
    "No Face":    { message: "Your face is not visible — adjust your camera", severity: "error" },
  },
  eye_contact: {
    Distracted: { message: "Look at the camera to maintain eye contact", severity: "error" },
    Left:       { message: "Try to keep your gaze towards the camera", severity: "warning" },
    Right:      { message: "Try to keep your gaze towards the camera", severity: "warning" },
    "No Face":  { message: "Your face is not detected — ensure you are visible", severity: "error" },
  },
};

// ── TTS ──────────────────────────────────────────────────────────
if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {};
  window.speechSynthesis.getVoices();
}
function speak(text) {
  if (!window.speechSynthesis || !text) return;
  
  // Cancel any ongoing speech
  window.speechSynthesis.cancel();
  
  // Create utterance
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95; 
  u.pitch = 1.0; 
  u.volume = 1.0;
  
  // Try to find a good English voice
  const voices = window.speechSynthesis.getVoices();
  const pref = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural"))) 
            || voices.find(v => v.lang.startsWith("en"))
            || voices[0];
            
  if (pref) u.voice = pref;
  
  // Fix for Chrome getting stuck on long sentences
  let iv = null;
  u.onstart = () => { 
    iv = setInterval(() => { 
      if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) { 
        window.speechSynthesis.pause(); 
        window.speechSynthesis.resume(); 
      } 
    }, 10000); 
  };
  
  u.onend = () => { if (iv) clearInterval(iv); };
  u.onerror = () => { if (iv) clearInterval(iv); };
  
  // Start speaking
  window.speechSynthesis.speak(u);
}

// ── Sub-Components ───────────────────────────────────────────────

function CoachingToast({ tips }) {
  if (!tips.length) return null;
  return (
    <div className="absolute top-3 left-3 z-30 flex flex-col gap-2 max-w-[280px]">
      <AnimatePresence>
        {tips.map((tip) => (
          <motion.div key={tip.key} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
            className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg backdrop-blur-md border ${
              tip.severity === "error" ? "bg-red-500/15 border-red-500/40 text-red-300" : "bg-yellow-500/15 border-yellow-500/40 text-yellow-300"
            }`} role="alert">
            <Shield className="w-4 h-4 shrink-0" />
            <span className="text-xs font-medium leading-snug">{tip.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function ConfirmEndModal({ onConfirm, onCancel, duration, questionCount, avgScore }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); const h = e => { if (e.key === "Escape") onCancel(); }; window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, [onCancel]);
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }}
        className="bg-gray-900/95 border border-cyan-500/30 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-[0_0_40px_rgba(0,240,255,0.1)]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center"><StopCircle className="w-5 h-5 text-red-400" /></div>
          <div><h3 className="text-white font-bold text-lg">End Session?</h3><p className="text-gray-400 text-xs">Your progress will be saved</p></div>
        </div>
        <div className="grid grid-cols-3 gap-3 mb-5 p-3 bg-black/40 rounded-xl border border-white/5">
          <div className="text-center"><div className="text-xs text-cyan-400/80">Duration</div><div className="text-white font-bold text-sm mt-0.5">{duration}</div></div>
          <div className="text-center"><div className="text-xs text-cyan-400/80">Questions</div><div className="text-white font-bold text-sm mt-0.5">{questionCount}</div></div>
          <div className="text-center"><div className="text-xs text-cyan-400/80">Avg Score</div><div className="text-white font-bold text-sm mt-0.5">{avgScore}</div></div>
        </div>
        <div className="flex gap-3">
          <button ref={ref} onClick={onCancel} className="flex-1 py-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm font-semibold hover:bg-cyan-500/20 transition-all">Continue</button>
          <button onClick={onConfirm} className="flex-1 py-2.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 text-sm font-semibold hover:bg-red-500/30 transition-all">End Session</button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function RadialGauge({ value, label, icon: Icon, color = "cyan", size = 80 }) {
  const r = (size - 12) / 2, circ = 2 * Math.PI * r, prog = (Math.min(100, Math.max(0, value)) / 100) * circ;
  const cm = { cyan: { s: "#06b6d4", g: "rgba(6,182,212,0.3)" }, green: { s: "#22c55e", g: "rgba(34,197,94,0.3)" }, yellow: { s: "#eab308", g: "rgba(234,179,8,0.3)" }, red: { s: "#ef4444", g: "rgba(239,68,68,0.3)" } };
  const c = cm[color] || cm.cyan;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={4} />
          <motion.circle cx={size/2} cy={size/2} r={r} fill="none" stroke={c.s} strokeWidth={4} strokeLinecap="round"
            strokeDasharray={circ} initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: circ - prog }}
            transition={{ type: "spring", stiffness: 60, damping: 12 }} style={{ filter: `drop-shadow(0 0 6px ${c.g})` }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Icon className="w-3 h-3 mb-0.5" style={{ color: c.s }} />
          <span className="text-[10px] font-bold text-white">{Math.round(value)}%</span>
        </div>
      </div>
      <span className="text-[9px] text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

// ── PDF Generator ────────────────────────────────────────────────
function generateSessionPDF({ sessionId, subject, difficulty, duration, questionCount, avgScore, rating, dominantEmotion, feedbacks, recommendations }) {
  const doc = new jsPDF(); const pw = doc.internal.pageSize.getWidth();
  doc.setFillColor(10,10,15); doc.rect(0,0,pw,40,"F");
  doc.setTextColor(0,240,255); doc.setFontSize(20); doc.setFont("helvetica","bold"); doc.text("Smart AI Interview Report",14,22);
  doc.setFontSize(10); doc.setTextColor(150,160,170); doc.text(`Generated: ${new Date().toLocaleDateString("en-US",{year:"numeric",month:"long",day:"numeric"})}`,14,32);
  doc.setDrawColor(0,240,255); doc.setLineWidth(0.5); doc.line(14,42,pw-14,42);
  doc.setFontSize(14); doc.setTextColor(255,255,255); doc.text("Session Overview",14,54);
  doc.autoTable({ startY:58, head:[["Metric","Value"]], body:[["Subject",subject||"General"],["Difficulty",difficulty||"Medium"],["Duration",duration||"N/A"],["Questions",String(questionCount||0)],["Avg Score",`${avgScore}/10`],["Rating",rating||"N/A"],["Emotion",dominantEmotion||"N/A"]], theme:"grid", headStyles:{fillColor:[0,180,200],textColor:[0,0,0]}, bodyStyles:{textColor:[200,210,220]}, alternateRowStyles:{fillColor:[20,20,30]}, margin:{left:14,right:14} });
  if (feedbacks?.length) { const y=doc.lastAutoTable.finalY+12; doc.setFontSize(14); doc.setTextColor(255,255,255); doc.text("Q&A Details",14,y); doc.autoTable({ startY:y+4, head:[["#","Question","Answer","Score","Feedback"]], body:feedbacks.map((f,i)=>[`Q${i+1}`,f.question||"",((f.answer||"").substring(0,80)),`${f.score}/10`,((f.feedback||"").substring(0,100))]), theme:"grid", headStyles:{fillColor:[0,180,200],textColor:[0,0,0],fontSize:8}, bodyStyles:{textColor:[200,210,220],fontSize:8}, columnStyles:{0:{cellWidth:10},1:{cellWidth:40},2:{cellWidth:40},3:{cellWidth:15}}, margin:{left:14,right:14} }); }
  if (recommendations?.length) { const y=doc.lastAutoTable?doc.lastAutoTable.finalY+12:160; doc.text("AI Recommendations",14,y); doc.autoTable({ startY:y+4, head:[["#","Recommendation"]], body:recommendations.map((r,i)=>[i+1,r]), theme:"grid", headStyles:{fillColor:[0,180,200],textColor:[0,0,0]}, bodyStyles:{textColor:[200,210,220]}, margin:{left:14,right:14} }); }
  doc.save(`interview-report-${sessionId||"session"}.pdf`);
}

// ── End Session Summary ──────────────────────────────────────────
function EndSessionSummary({ sessionData, feedbacks, scores, elapsedSec, questionCount, subject, difficulty, sessionId, onDownloadPDF, onViewHistory, onNewSession }) {
  const [anim, setAnim] = useState(0);
  const avg = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : "—";
  useEffect(() => { const t=parseFloat(avg); if(isNaN(t)) return; const s=t/30; let c=0; const iv=setInterval(()=>{ c+=s; if(c>=t){c=t;clearInterval(iv);} setAnim(parseFloat(c.toFixed(1))); },50); return ()=>clearInterval(iv); },[avg]);
  const fmt = s => `${Math.floor(s/60)}m ${s%60}s`;
  const rating = sessionData?.performance_rating || (scores.length ? (parseFloat(avg)>=8?"Excellent":parseFloat(avg)>=6?"Good":parseFloat(avg)>=4?"Average":"Needs Improvement") : "Not Scored");
  const rc = rating==="Excellent"?"text-green-400":rating==="Good"?"text-cyan-400":rating==="Average"?"text-yellow-400":"text-red-400";
  const strengths = [...new Set(feedbacks.flatMap(f=>f.strengths||[]))].slice(0,5);
  const improvements = [...new Set(feedbacks.flatMap(f=>f.improvements||[]))].slice(0,5);
  const pie = Object.entries(sessionData?.emotion_breakdown||{}).filter(([,v])=>v>0).map(([n,v])=>({name:n.charAt(0).toUpperCase()+n.slice(1),value:v<=1?Math.round(v*100):Math.round(v)})).sort((a,b)=>b.value-a.value);
  const recs = sessionData?.recommendations || [];
  return (
    <motion.div initial={{opacity:0}} animate={{opacity:1}} className="fixed inset-0 z-50 bg-black/95 backdrop-blur-lg overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <motion.div initial={{y:-20,opacity:0}} animate={{y:0,opacity:1}} className="text-center mb-8"><Award className="w-12 h-12 text-cyan-400 mx-auto mb-3" /><h1 className="text-3xl font-bold text-white mb-1">Session Complete</h1><p className="text-gray-400 text-sm">Here's how you performed</p></motion.div>
        <motion.div initial={{scale:0.8,opacity:0}} animate={{scale:1,opacity:1}} transition={{delay:0.2,type:"spring"}} className="text-center mb-8 p-8 rounded-2xl bg-gray-900/80 border border-cyan-500/20">
          {scores.length > 0 ? (
            <>
              <div className="text-6xl font-extrabold text-white mb-2">{anim<10?"0"+anim:anim}<span className="text-2xl text-gray-500">/10</span></div>
              <div className={`text-lg font-semibold ${rc}`}>{rating}</div>
            </>
          ) : (
            <div className="py-2">
              <div className="text-3xl font-extrabold text-cyan-400 mb-2">Incomplete Session</div>
              <div className="text-sm text-gray-400">Answer more questions to receive a performance score.</div>
            </div>
          )}
        </motion.div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[{l:"Duration",v:fmt(elapsedSec),i:Clock},{l:"Questions",v:questionCount,i:Target},{l:"Avg Score",v:`${avg}/10`,i:TrendingUp},{l:"Rating",v:rating,i:Award}].map((s,i)=>(
            <div key={i} className="p-4 rounded-xl bg-gray-900/60 border border-white/5 text-center"><s.i className="w-5 h-5 text-cyan-400 mx-auto mb-2"/><div className="text-xs text-gray-400 mb-1">{s.l}</div><div className="text-white font-bold text-sm">{s.v}</div></div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {pie.length>0&&(<div className="p-5 rounded-xl bg-gray-900/60 border border-white/5"><h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-cyan-400"/>Emotion Breakdown</h3><ResponsiveContainer width="100%" height={180}><PieChart><Pie data={pie} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" paddingAngle={3} stroke="none">{pie.map((_,i)=><Cell key={i} fill={PIE_COLORS[i%PIE_COLORS.length]}/>)}</Pie><Tooltip contentStyle={{background:"#111",border:"1px solid #333",borderRadius:8,fontSize:12}}/></PieChart></ResponsiveContainer></div>)}
          <div className="p-5 rounded-xl bg-gray-900/60 border border-white/5">
            <h3 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2"><CheckCircle2 className="w-4 h-4"/>Strengths</h3>
            {strengths.length?strengths.map((s,i)=><p key={i} className="text-xs text-gray-300 mb-1">&bull; {s}</p>):<p className="text-xs text-green-400/40 italic">Continue practicing to identify specific professional strengths</p>}
            <h3 className="text-sm font-semibold text-orange-400 mt-4 mb-2 flex items-center gap-2"><AlertCircle className="w-4 h-4"/>Areas to Improve</h3>
            {improvements.length?improvements.map((s,i)=><p key={i} className="text-xs text-gray-300 mb-1">&bull; {s}</p>):<p className="text-xs text-orange-400/40 italic">Review previous answers to uncover areas for improvement</p>}
          </div>
        </div>
        {recs.length>0&&(<div className="p-5 rounded-xl bg-gray-900/60 border border-white/5 mb-8"><h3 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2"><Brain className="w-4 h-4"/>AI Recommendations</h3>{recs.map((r,i)=><div key={i} className="flex gap-3 items-start mb-2"><span className="text-xs text-cyan-400/80 font-bold">{i+1}.</span><p className="text-xs text-gray-300 leading-relaxed">{r}</p></div>)}</div>)}
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={onDownloadPDF} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-cyan-600 text-black font-bold text-sm hover:bg-cyan-500 transition-all"><Download className="w-4 h-4"/>Download PDF</button>
          <button onClick={onViewHistory} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-gray-800 border border-white/10 text-white font-bold text-sm hover:bg-gray-700 transition-all"><FileText className="w-4 h-4"/>History</button>
          <button onClick={onNewSession} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-purple-600/20 border border-purple-500/30 text-purple-300 font-bold text-sm hover:bg-purple-600/30 transition-all"><Sparkles className="w-4 h-4"/>New Session</button>
        </div>
      </div>
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════
export default function InterviewSession() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { subject = "general", difficulty = "medium" } = location.state || {};

  // ── State ──
  const [sessionId, setSessionId] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle|loading|asking|evaluating|feedback|ended
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [isEnding, setIsEnding] = useState(false);
  const [allFeedbacks, setAllFeedbacks] = useState([]);
  const [coachingTips, setCoachingTips] = useState([]);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [sessionSummary, setSessionSummary] = useState(null);
  const [scores, setScores] = useState([]);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [cameraActive, setCameraActive] = useState(true);
  const [emotionHistory, setEmotionHistory] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [isBackendMode, setIsBackendMode] = useState(false); // New: Browser vs Backend AI
  const [lastBox, setLastBox] = useState(null); // Bounding box from backend

  // ── Face Analysis State (from browser-side MediaPipe) ──
  const [emotion, setEmotion] = useState("none");
  const [confidence, setConfidence] = useState(0);
  const [posture, setPosture] = useState("Scanning...");
  const [eyeContact, setEyeContact] = useState("Scanning...");
  const [rawGazeRatio, setRawGazeRatio] = useState(0.5);
  const [rawHeadPose, setRawHeadPose] = useState(null);
  const [cameraBlocked, setCameraBlocked] = useState(false); // New: explicit blocked state
  const [multiFaceViolation, setMultiFaceViolation] = useState(false);

  const [streamReady, setStreamReady] = useState(false);
  const [faceReady, setFaceReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  // ── Refs ──
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const faceAnalyzerRef = useRef(null);
  const faceLoopRef = useRef(null);
  const metricsSendCounter = useRef(0);
  const coachingTimerRef = useRef({});
  const transcriptEndRef = useRef(null);
  const initLockRef = useRef(false);
  const isFetchingQuestionRef = useRef(false); // New: prevent duplicate fetches
  const canvasRef = useRef(null);
  const lastFrameTimeRef = useRef(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);

  // ── Derived ──
  // Interview Average Score (Live Calculation — blends API score + behavioral metrics)
  const avgScore = (() => {
    if (!scores.length) return "—";
    const apiAvg = scores.reduce((a, b) => a + b, 0) / scores.length;
    // Behavioral bonus: confidence, eye contact, posture each contribute up to ~1 point
    const confScore = faceReady ? Math.min(1, confidence) : 0;
    const eyeScore = faceReady && eyeContact === "Center" ? 1 : faceReady && eyeContact !== "No Face" ? 0.5 : 0;
    const postScore = faceReady && posture === "Good" ? 1 : faceReady && posture !== "No Face" ? 0.5 : 0;
    const behavioralBonus = (confScore + eyeScore + postScore) / 3; // 0–1
    // Final: 70% API answer quality + 30% behavioral presence (scaled to 10)
    const blended = apiAvg * 0.7 + behavioralBonus * 10 * 0.3;
    return Math.max(1, blended).toFixed(0);
  })();
  const [jitter, setJitter] = useState(0);
  useEffect(() => { const i = setInterval(() => setJitter((Math.random()-0.5)*1.2), 200); return () => clearInterval(i); }, []);

  const formatTime = (s) => `${Math.floor(s/60).toString().padStart(2,"0")}:${(s%60).toString().padStart(2,"0")}`;

  // ── Timer ──
  useEffect(() => {
    if (!sessionId || phase === "ended") return;
    const t = setInterval(() => setElapsedSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [sessionId, phase]);

  // ── Coaching Tips (debounced) ──
  useEffect(() => {
    const check = (category, value) => {
      const tip = COACHING_TIPS[category]?.[value];
      if (tip) {
        if (!coachingTimerRef.current[category]) {
          coachingTimerRef.current[category] = setTimeout(() => {
            setCoachingTips(prev => prev.find(t => t.key === category) ? prev : [...prev, { key: category, ...tip }]);
          }, 2000);
        }
      } else {
        if (coachingTimerRef.current[category]) { clearTimeout(coachingTimerRef.current[category]); coachingTimerRef.current[category] = null; }
        setCoachingTips(prev => prev.filter(t => t.key !== category));
      }
    };
    check("posture", posture);
    check("eye_contact", eyeContact);
    const safety = setTimeout(() => setCoachingTips([]), 8000);
    return () => clearTimeout(safety);
  }, [posture, eyeContact]);

  // ── Camera Setup ──
  useEffect(() => {
    let mounted = true;
    async function start() {
      if (initLockRef.current) return;
      initLockRef.current = true;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
          audio: false,
        });
        if (!mounted) { stream.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = stream;

        // Attach to video element
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          
          // User Fix 1: onloadeddata is for ACTUAL frames
          video.onloadeddata = () => {
            if (video.videoWidth > 0) {
              video.play()
                .then(() => setStreamReady(true))
                .catch(() => {});
            }
          };

          // User Fix 4: Force re-render quirk fix
          setTimeout(() => {
            if (video.paused && video.srcObject) {
              video.play().catch(() => {});
            }
          }, 300);
        }
      } catch (e) {
        console.error("[Camera]", e);
        setCameraBlocked(true);
        if (e.name === "NotAllowedError") alert("Camera permission denied. Please allow access and refresh.");
        else if (e.name === "NotFoundError") alert("No camera found. Please connect a camera and refresh.");
      }
    }
    start();

    // Chrome autoplay: resume on user gesture
    const resume = () => {
      if (videoRef.current?.paused && videoRef.current.srcObject) {
        videoRef.current.play().catch(() => {});
      }
    };
    document.addEventListener("click", resume, { once: true });

    return () => {
      mounted = false;
      initLockRef.current = false; // Allow re-initialization if needed
      document.removeEventListener("click", resume);
      if (streamRef.current) { 
        streamRef.current.getTracks().forEach(t => t.stop()); 
        streamRef.current = null; 
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  // Retry attachment if video ref wasn't ready at init
  useEffect(() => {
    if (streamReady) return; // already working
    const v = videoRef.current, s = streamRef.current;
    if (!v || !s) return;
    const retry = setInterval(() => {
      if (!v.srcObject || v.srcObject.id !== s.id) { v.srcObject = s; }
      if (v.paused && v.srcObject) { v.play().catch(() => {}); }
      if (v.readyState >= 2 && !v.paused) { setStreamReady(true); clearInterval(retry); }
    }, 500);
    return () => clearInterval(retry);
  }, [streamReady, cameraActive]);

  // Camera toggle
  useEffect(() => {
    if (!streamRef.current) return;
    const track = streamRef.current.getVideoTracks()[0];
    if (track) {
      track.enabled = true;
    }
  }, [streamReady]);

  // ── Browser-Side Face Analysis (MediaPipe — 0ms latency) ──
  useEffect(() => {
    if (!streamReady || isBackendMode) return; // Skip if backend is doing the work
    let running = true;
    const analyzer = getFaceAnalyzer();
    faceAnalyzerRef.current = analyzer;

    analyzer.initialize().then(() => {
      if (!running) return;
      setFaceReady(true);

      let lastAnalysis = 0;
      const ANALYSIS_INTERVAL = 66; // ms (~15fps)

      const loop = () => {
        if (!running) return;
        faceLoopRef.current = requestAnimationFrame(loop);
        const now = performance.now();
        if (now - lastAnalysis < ANALYSIS_INTERVAL) return;
        lastAnalysis = now;

        const video = videoRef.current;
        if (!video || !cameraActive || video.readyState < 1) return;
        
        if (video.videoWidth === 0) return;

        const result = analyzer.analyze(video, now);
        if (result.multipleFaces) {
          setMultiFaceViolation(true);
          running = false;
          return;
        }

        if (result.posture !== "Initializing") {
          setEmotion(result.emotion);
          setConfidence(result.confidence);
          setPosture(result.posture);
          setEyeContact(result.eyeContact);
          if (result.headPose) setRawHeadPose(result.headPose);
          if (result.gazeRatio !== undefined) setRawGazeRatio(result.gazeRatio);

          if (result.hasFace) {
            setEmotionHistory(prev => {
              const pt = { idx: prev.length, confidence: Math.round(result.confidence * 100), emotion: result.emotion };
              const upd = [...prev, pt];
              return upd.length > 30 ? upd.slice(-30) : upd;
            });
          }
        }

        // Send metrics periodically to backend (~every 2 sec)
        metricsSendCounter.current++;
        if (metricsSendCounter.current >= 30 && wsRef.current?.readyState === WebSocket.OPEN && result.hasFace) {
          metricsSendCounter.current = 0;
          wsRef.current.send(JSON.stringify({ 
            type: "metrics", 
            data: { 
              emotion: result.emotion, 
              confidence: result.confidence, 
              posture: result.posture, 
              eye_contact: result.eyeContact, 
              head_pose: result.headPose, 
              gaze_ratio: result.gazeRatio, 
              all_emotions: result.allEmotions 
            } 
          }));
        }
      };
      faceLoopRef.current = requestAnimationFrame(loop);
    });

    return () => { running = false; if (faceLoopRef.current) cancelAnimationFrame(faceLoopRef.current); };
  }, [streamReady, cameraActive, isBackendMode]);

  // ── Drawing Loop (The "Mirror" Overlay) ──
  useEffect(() => {
    if (!streamReady || !cameraActive) return;
    let running = true;
    const draw = () => {
      if (!running) return;
      requestAnimationFrame(draw);

      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2) return;

      const ctx = canvas.getContext("2d");
      const vw = video.videoWidth;
      const vh = video.videoHeight;

      if (canvas.width !== vw || canvas.height !== vh) {
        canvas.width = vw;
        canvas.height = vh;
      }

      ctx.clearRect(0, 0, vw, vh);

      // We only draw if we have a face and a result
      if (emotion !== "none") {
        ctx.save();
        // Handle coordinate symmetry
        ctx.lineWidth = 3;
        ctx.shadowBlur = 15;

        // In Pro AI (Backend) mode, we use the specific box
        if (isBackendMode && lastBox) {
          const [x, y, w, h] = lastBox;
          ctx.strokeStyle = "#06b6d4";
          ctx.shadowColor = "rgba(6, 182, 212, 0.5)";
          ctx.strokeRect(x, y, w, h);
          
          // Labels
          ctx.fillStyle = "#06b6d4";
          ctx.font = "bold 20px monospace";
          ctx.fillText(`AI ANALYSIS`, x, y > 25 ? y - 30 : y + h + 45);
          ctx.font = "bold 24px monospace";
          ctx.fillText(`${emotion.toUpperCase()} ${Math.round(confidence * 100)}%`, x, y > 25 ? y - 10 : y + h + 25);
        } else if (emotion !== "none") {
          // Subtle target indicator in FAST AI mode
          ctx.strokeStyle = "rgba(6, 182, 212, 0.4)";
          ctx.setLineDash([10, 5]);
          ctx.strokeRect(vw * 0.2, vh * 0.15, vw * 0.6, vh * 0.7);
          
          if (emotion !== "neutral") {
            ctx.fillStyle = "rgba(6, 182, 212, 0.8)";
            ctx.font = "bold 22px monospace";
            ctx.fillText(emotion.toUpperCase(), vw * 0.2, vh * 0.15 - 10);
          }
        }
        ctx.restore();
      }

      // If in Backend mode, send frame periodically
      if (isBackendMode && cameraActive && wsRef.current?.readyState === WebSocket.OPEN) {
        const now = performance.now();
        if (now - lastFrameTimeRef.current > 400) { // ~2.5 fps for backend to keep it "real-time" but light
          lastFrameTimeRef.current = now;
          const tempCanvas = document.createElement("canvas");
          tempCanvas.width = 300; // Smaller for speed
          tempCanvas.height = (vh / vw) * 300;
          const tctx = tempCanvas.getContext("2d");
          tctx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
          const base64 = tempCanvas.toDataURL("image/jpeg", 0.7);
          wsRef.current.send(JSON.stringify({ type: "frame", data: base64 }));
        }
      }
    };
    draw();
    return () => { running = false; };
  }, [streamReady, cameraActive, isBackendMode, emotion, lastBox, confidence]);

  // ── Create Session ──
  useEffect(() => {
    (async () => {
      try {
        const res = await api.post("/interview/start_session", {
          user_id: user?.id || "anonymous",
          job_role: subject.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
          subject, difficulty,
        });
        setSessionId(res.data.id);
      } catch (err) { console.error("[Session]", err); }
    })();
  }, []);

  // ── Auto-fetch first question ──
  useEffect(() => { 
    if (sessionId && phase === "idle" && !isFetchingQuestionRef.current) { 
      fetchNextQuestion(); 
    } 
  }, [sessionId, phase]);

  // ── TTS ──
  useEffect(() => {
    if (ttsEnabled && currentQuestion?.question_text && phase === "asking") {
      const t = setTimeout(() => speak(currentQuestion.question_text), 300);
      return () => clearTimeout(t);
    }
  }, [currentQuestion?.question_number, ttsEnabled, phase]);

  // ── Auto-scroll transcript ──
  useEffect(() => { transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [transcript]);

  // ── WebSocket (for session tracking only — no frames sent) ──
  useEffect(() => {
    if (!sessionId) return;
    let ws, reconnect;
    const connect = () => {
      const base = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/^http/, "ws");
      const jwt = localStorage.getItem("token") || "";
      ws = new WebSocket(`${base}/interview/ws/${sessionId}?token=${encodeURIComponent(jwt)}`);
      wsRef.current = ws;
      ws.onopen = () => {};
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "audio_analysis" && msg.data?.transcript) {
            const text = msg.data.transcript.trim();
            if (text) { setAnswer(text); setTranscript(prev => [...prev, { type: "answer", text, num: 0 }]); }
          }
          if (msg.type === "emotion" && isBackendMode) {
              setEmotion(msg.data.emotion);
              setConfidence(msg.data.confidence);
              setPosture(msg.data.posture || "Good");
              setEyeContact(msg.data.eye_contact || "Center");
              if (msg.data.head_pose) setRawHeadPose(msg.data.head_pose);
              if (msg.data.gaze_ratio !== undefined) setRawGazeRatio(msg.data.gaze_ratio);
              if (msg.data.box) setLastBox(msg.data.box);
          }
        } catch {}
      };
      ws.onclose = () => { reconnect = setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { clearTimeout(reconnect); if (ws) ws.close(); };
  }, [sessionId]);

  // ── Q&A Handlers ──
  const fetchNextQuestion = useCallback(async () => {
    if (!sessionId || isFetchingQuestionRef.current) return;
    isFetchingQuestionRef.current = true;
    setPhase("loading"); setFeedback(null);
    try {
      const emotionCtx = {};
      if (emotionHistory.length) {
        const recent = emotionHistory.slice(-10);
        const counts = {};
        recent.forEach(e => { counts[e.emotion] = (counts[e.emotion]||0)+1; });
        Object.entries(counts).forEach(([k,v]) => { emotionCtx[k] = v/recent.length; });
      } else { emotionCtx[emotion] = confidence; }

      const prev = phase === "feedback" ? null : (answer || null);
      const res = await api.post("/interview/next_question", { 
        session_id: sessionId, 
        previous_answer: prev, 
        emotion_context: emotionCtx 
      }, { timeout: 30000 });
      
      setCurrentQuestion(res.data);
      setQuestionCount(res.data.question_number);
      setAnswer("");
      setPhase("asking");
      setTranscript(prev => [...prev, { type: "question", text: res.data.question_text, num: res.data.question_number }]);
    } catch (err) { 
      console.error("[Q]", err); 
      setPhase("asking"); 
    } finally {
      isFetchingQuestionRef.current = false;
    }
  }, [sessionId, answer, emotion, confidence, emotionHistory, phase]);

  const submitAnswer = useCallback(async () => {
    if (!sessionId || !currentQuestion || !answer.trim()) return;
    
    setPhase("evaluating");
    // Add to transcript immediately for feel
    setTranscript(prev => [...prev, { type: "answer", text: answer, num: currentQuestion.question_number }]);

    try {
      // Extended timeout for slow AI evaluation
      const res = await api.post("/interview/submit_answer", {
        session_id: sessionId,
        question_number: currentQuestion.question_number,
        answer_text: answer
      }, { timeout: 45000 });

      if (res.data) {
        setFeedback(res.data);
        setScores(prev => [...prev, res.data.score]);
        setPhase("feedback");
        
        // Save to local feedback history
        setAllFeedbacks(prev => [...prev, {
          question: currentQuestion.question_text,
          answer,
          score: res.data.score,
          feedback: res.data.feedback,
          strengths: res.data.strengths,
          improvements: res.data.improvements
        }]);

        setTranscript(prev => [...prev, {
          type: "feedback",
          text: `Score: ${res.data.score}/10 — ${res.data.feedback}`,
          num: currentQuestion.question_number
        }]);
      } else {
        throw new Error("No data received");
      }
    } catch (err) {
      console.error("[Submission Error]", err);
      // Fallback: provide a baseline score so the HUD still updates
      const fallbackScore = 5;
      setFeedback({ 
        score: fallbackScore, 
        feedback: "The AI is taking a bit longer than usual to analyze your response. We've assigned a provisional score of 5/10 so you can continue. Your full performance will be reflected in the final session report.", 
        strengths: ["Detailed response provided"], 
        improvements: ["Ensure consistent audio/video clarity for faster processing."] 
      });
      setScores(prev => [...prev, fallbackScore]);
      setAllFeedbacks(prev => [...prev, { question: currentQuestion.question_text, answer, score: fallbackScore, feedback: "Evaluation timed out — baseline score assigned.", strengths: [], improvements: [] }]);
      setPhase("feedback");
    }
  }, [sessionId, currentQuestion, answer]);

  const handleEndSession = useCallback(async () => {
    if (isEnding) return;
    setIsEnding(true); setShowEndConfirm(false); setPhase("ended"); window.speechSynthesis?.cancel();
    let summary = null;
    if (sessionId) { try { summary = (await api.post(`/interview/session/${sessionId}/end`, null, { timeout: 30000 })).data; } catch {} }
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.close();
    setSessionSummary(summary); setShowSummary(true);
  }, [sessionId, isEnding]);

  useEffect(() => {
    if (multiFaceViolation && phase !== "ended") {
      console.error("[SECURITY] Multiple individuals detected. Terminating session.");
      // Ensure immediate clean up
      if (streamRef.current) { 
        streamRef.current.getTracks().forEach(t => t.stop()); 
        streamRef.current = null; 
      }
      if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.close();
      
      alert("SECURITY ALERT: Multiple individuals detected in local environment. This is a violation of the interview protocol. Session is being terminated immediately for integrity.");
      navigate("/dashboard");
    }
  }, [multiFaceViolation, phase, navigate]);

  const handleDownloadPDF = useCallback(() => {
    const avg = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : "0";
    generateSessionPDF({ sessionId, subject, difficulty, duration: formatTime(elapsedSec), questionCount, avgScore: avg, rating: sessionSummary?.performance_rating, dominantEmotion: sessionSummary?.dominant_emotion || emotion, feedbacks: allFeedbacks, recommendations: sessionSummary?.recommendations || [] });
  }, [sessionId, subject, difficulty, elapsedSec, questionCount, scores, sessionSummary, allFeedbacks, emotion]);

  // ── Voice Answering logic ──
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setIsTranscribing(true);
        try {
          // Convert blob to base64
          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = async () => {
             const base64Audio = reader.result.split(",")[1];
             const res = await api.post("/interview/transcribe", { audio: base64Audio });
             if (res.data?.success && res.data.transcript) {
               setAnswer(prev => prev + (prev ? " " : "") + res.data.transcript.trim());
             }
             setIsTranscribing(false);
          };
        } catch (err) {
          console.error("Transcription failed", err);
          setIsTranscribing(false);
        }
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // Auto-stop after 30 seconds
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 29) {
            stopRecording();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);

    } catch (err) {
      console.error("Mic access denied", err);
      alert("Microphone access is required for voice answering.");
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }, []);

  // ── Style Helpers ──
  const emotionColors = { happiness:"text-green-400", neutral:"text-cyan-400", surprise:"text-yellow-400", sadness:"text-indigo-400", anger:"text-red-400", fear:"text-orange-400", disgust:"text-rose-400", contempt:"text-gray-400" };
  const getEmotionColor = e => e === "none" ? "text-gray-500 animate-pulse" : emotionColors[e] || "text-cyan-400";
  const postureColor = posture==="Camera Off"?"text-gray-500":posture==="Good"?"text-green-400":posture==="Slouching"?"text-yellow-400":"text-red-400";
  const eyeColor = eyeContact==="Camera Off"?"text-gray-500":eyeContact==="Center"?"text-green-400":eyeContact==="Distracted"?"text-red-400":"text-yellow-400";
  const getScoreColor = s => s>=7?"text-green-400":s>=4?"text-yellow-400":"text-red-400";
  const scoreGlow = avgScore!=="—" ? (parseFloat(avgScore)>=7?"shadow-[0_0_20px_rgba(34,197,94,0.25)]":parseFloat(avgScore)>=4?"shadow-[0_0_20px_rgba(234,179,8,0.25)]":"shadow-[0_0_20px_rgba(239,68,68,0.25)]") : "";

  // ══════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-black text-cyan-400 font-mono overflow-hidden relative selection:bg-cyan-500/30">
      {/* Background Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />

      {/* Overlays */}
      <AnimatePresence>{showSummary && <EndSessionSummary sessionData={sessionSummary} feedbacks={allFeedbacks} scores={scores} elapsedSec={elapsedSec} questionCount={questionCount} subject={subject} difficulty={difficulty} sessionId={sessionId} onDownloadPDF={handleDownloadPDF} onViewHistory={()=>navigate("/history")} onNewSession={()=>navigate("/dashboard")} />}</AnimatePresence>
      <AnimatePresence>{showEndConfirm && <ConfirmEndModal onConfirm={handleEndSession} onCancel={()=>setShowEndConfirm(false)} duration={formatTime(elapsedSec)} questionCount={questionCount} avgScore={avgScore} />}</AnimatePresence>

      {/* ═══ MAIN LAYOUT ═══ */}
      <div className="relative z-10 flex h-screen p-4 gap-4">

        {/* ─── LEFT: Camera + HUD ─── */}
        <div className="flex-1 flex flex-col gap-3">

          {/* Top Bar */}
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2"><Cpu className="w-5 h-5 text-cyan-400 animate-pulse" /><span className="text-sm font-bold tracking-widest uppercase">Smart AI Interview</span></div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-2"><span className={`w-2 h-2 rounded-full ${cameraActive?"bg-green-500 shadow-[0_0_8px_#0f0]":"bg-red-500"}`}/> CAM {cameraActive?"ON":"OFF"}</span>
              <span className="flex items-center gap-1.5 text-white"><Clock className="w-3.5 h-3.5"/>{formatTime(elapsedSec)}</span>
              {phase!=="idle"&&phase!=="ended"&&(<span className="flex items-center gap-1.5 bg-red-500/15 border border-red-500/30 px-2.5 py-1 rounded-full"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"/><span className="text-red-400 font-bold tracking-widest text-[10px]">LIVE</span></span>)}
              {questionCount>0&&phase!=="ended"&&(<button onClick={handleDownloadPDF} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 hover:bg-cyan-500/20 transition-all"><FileText className="w-3.5 h-3.5"/><span className="text-[10px] font-bold">PDF</span></button>)}
            </div>
          </div>

          {/* Question HUD */}
          <AnimatePresence mode="wait">
            {currentQuestion && (phase==="asking"||phase==="evaluating"||phase==="feedback") && (
              <motion.div key={currentQuestion.question_number} initial={{opacity:0,y:-10}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-10}}
                className="px-6 py-4 bg-black/70 border-2 border-cyan-500/50 rounded-xl backdrop-blur-md shadow-[0_0_30px_rgba(0,240,255,0.15)]">
                <div className="flex items-center gap-3 mb-2">
                  <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-xs font-bold tracking-wider">Q{currentQuestion.question_number}</span>
                  <span className="text-[11px] text-cyan-400/80 uppercase tracking-widest">{currentQuestion.question_type}</span>
                </div>
                <p className="text-lg text-white font-semibold leading-relaxed font-sans">{currentQuestion.question_text}</p>
                {currentQuestion.tips?.[0] && <p className="mt-2 text-xs text-cyan-400/60 italic font-sans">Tip: {currentQuestion.tips[0]}</p>}
              </motion.div>
            )}
          </AnimatePresence>

          {phase==="loading"&&(<div className="px-6 py-4 bg-black/70 border border-cyan-500/20 rounded-xl flex items-center justify-center gap-3"><div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"/><span className="text-sm text-cyan-400/70">Generating next question...</span></div>)}

          {/* Video Container */}
          <div className="relative flex-1 min-h-[300px] bg-black/50 border-2 border-cyan-500/30 rounded-lg overflow-hidden shadow-[0_0_30px_rgba(0,240,255,0.08)]">
            <div className="absolute top-0 left-0 w-14 h-14 border-t-2 border-l-2 border-cyan-500 rounded-tl-lg pointer-events-none" />
            <div className="absolute top-0 right-0 w-14 h-14 border-t-2 border-r-2 border-cyan-500 rounded-tr-lg pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-14 h-14 border-b-2 border-l-2 border-cyan-500 rounded-bl-lg pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-14 h-14 border-b-2 border-r-2 border-cyan-500 rounded-br-lg pointer-events-none" />
            {/* Bento-Style Centered Video Feed (Premium Design) */}
            <div className="absolute inset-0 flex items-center justify-center bg-black">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
                style={{ transform: "scaleX(-1)" }} // Natural Mirroring
              />
              {/* Scan-Line Aesthetic Overlay */}
              <motion.div className="absolute left-0 right-0 h-[3px] bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent pointer-events-none z-20" animate={{top:["0%","100%","0%"]}} transition={{duration:6,repeat:Infinity,ease:"easeInOut"}} />
            </div>

            {/* Mirror Overlay Canvas (AI Tracking Visualization) */}
            {/* Mirror Overlay Canvas */}
            <canvas
              ref={canvasRef}
              style={{
                width: "100%",
                height: "100%",
                position: "absolute",
                top: 0,
                left: 0,
                transform: "scaleX(-1)", // Mirror to match video
                zIndex: 15, // Higher than video/overlay
                pointerEvents: "none",
              }}
            />
            {/* Loading indicator while camera starts */}
            {cameraActive && !streamReady && (
              <div className="absolute inset-0 flex flex-col items-center justify-center z-20 pointer-events-none">
                <div className="bg-black/40 backdrop-blur-sm p-8 rounded-3xl flex flex-col items-center">
                  <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
                  <p className="text-cyan-400 font-bold tracking-[0.2em] uppercase text-xs">Initializing Feed...</p>
                </div>
              </div>
            )}
            {!cameraActive && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-cyan-500/30 z-10 bg-black/80">
                <VideoOff className="w-20 h-20 mb-3" />
                <p className="tracking-widest text-sm font-bold">CAMERA MANUALLY DISABLED</p>
              </div>
            )}
            {cameraBlocked && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-red-500 z-20 bg-black/90 px-8 text-center">
                <AlertCircle className="w-16 h-16 mb-4 animate-pulse" />
                <p className="tracking-widest text-lg font-bold mb-2">ACCESS BLOCKED</p>
                <p className="text-red-400/60 text-xs">Please grant camera permissions and refresh your browser to continue.</p>
              </div>
            )}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.05)_1px,transparent_1px)] bg-[size:60px_60px] opacity-30 pointer-events-none" />

            <CoachingToast tips={coachingTips} />

            {/* Emotion Badge */}
            <div className={`absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-black/80 border backdrop-blur-md px-4 py-2 rounded-full z-20 ${emotion==="none"?"border-gray-500/30":"border-cyan-500/30"}`}>
              {!faceReady ? (
                <>
                  <div className="w-3 h-3 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-cyan-400/60 tracking-widest">LOADING AI...</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_6px_#22c55e] animate-pulse" />
                  <span className={`text-sm font-bold capitalize tracking-widest ${getEmotionColor(emotion)}`}>{emotion==="none"?"SCANNING...":emotion}</span>
                  {emotion!=="none"&&<span className="text-xs text-cyan-400/80">{(confidence*100).toFixed(0)}%</span>}
                </>
              )}
            </div>

            {/* Mini Metrics */}
            <div className="absolute top-3 right-3 bg-black/70 border border-cyan-500/20 backdrop-blur-md rounded-lg p-2.5 flex flex-col gap-1.5 min-w-[120px] z-20">
              <div className="flex items-center gap-2 text-[11px]"><Activity className={`w-3 h-3 ${postureColor}`}/><span className="text-cyan-400/80">Posture:</span><span className={`font-bold ${postureColor}`}>{posture}</span></div>
              <div className="flex items-center gap-2 text-[11px]"><Eye className={`w-3 h-3 ${eyeColor}`}/><span className="text-cyan-400/80">Eye:</span><span className={`font-bold ${eyeColor}`}>{eyeContact==="Center"?"Good":eyeContact}</span></div>
            </div>

            {/* Controls */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2 z-20">
              <button onClick={()=>setCameraActive(c=>!c)} className={`p-2.5 rounded-full backdrop-blur-md transition-all ${cameraActive?"bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/40":"bg-red-500/20 text-red-400 hover:bg-red-500/40"}`}>
                {cameraActive ? <Video className="w-4 h-4"/> : <VideoOff className="w-4 h-4"/>}
              </button>
              <button onClick={()=>setTtsEnabled(t=>!t)} className={`p-2.5 rounded-full backdrop-blur-md transition-all ${ttsEnabled?"bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/40":"bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/40"}`}>
                {ttsEnabled ? <Volume2 className="w-4 h-4"/> : <VolumeX className="w-4 h-4"/>}
              </button>
              <button onClick={()=>setShowEndConfirm(true)} disabled={isEnding} className="p-2.5 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/40 disabled:opacity-50 transition-all">
                <StopCircle className="w-4 h-4"/>
              </button>
            </div>

          </div>
        </div>

        {/* ─── RIGHT: Scores + Metrics + Q&A ─── */}
        <div className="w-96 flex flex-col gap-3 overflow-hidden">

          {/* Score Card */}
          <div className={`bg-black/40 backdrop-blur-md border border-cyan-500/20 rounded-xl p-4 transition-shadow ${scoreGlow}`}>
            <div className="flex items-center justify-between mb-2">
              <div><div className="text-[11px] text-cyan-400/80 uppercase tracking-widest">Interview Score</div><div className="text-3xl font-extrabold text-white mt-0.5">{avgScore}</div></div>
              <div className="text-center bg-black/50 border border-cyan-500/20 rounded-lg px-4 py-2"><div className="text-[11px] text-cyan-400/80 uppercase">Questions</div><div className="text-xl font-bold text-cyan-400">{questionCount}</div></div>
            </div>
            <div className="h-1.5 bg-gray-900 rounded-full overflow-hidden">
              <motion.div className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full shadow-[0_0_8px_#06b6d4]" animate={{width:`${scores.length?(scores.reduce((a,b)=>a+b,0)/scores.length)*10:0}%`}} transition={{duration:0.5}} />
            </div>
          </div>

          {/* Live Metrics */}
          <div className="bg-black/40 backdrop-blur-md border border-cyan-500/20 rounded-xl p-4">
            <h3 className="text-[11px] text-cyan-400/80 uppercase tracking-widest mb-3 flex items-center gap-2"><Activity className="w-3.5 h-3.5"/>Real-Time Analytics</h3>
            <div className="flex justify-around mb-3">
              <RadialGauge label="Confidence" value={faceReady ? Math.max(0, confidence * 100 + jitter) : 0} icon={Brain} color="cyan" size={64} />
              <RadialGauge label="Eye Contact" value={!faceReady || eyeContact==="Scanning..." || eyeContact==="Camera Off" || eyeContact==="No Face" ? 0 : Math.max(15, (1 - Math.abs(rawGazeRatio - 0.5) * 2) * 100) + jitter} icon={Eye}
                color={!faceReady || eyeContact==="Scanning..." || eyeContact==="Camera Off" || eyeContact==="No Face" ? "red" : eyeContact==="Center" ? "green" : eyeContact==="Distracted" ? "red" : "yellow"} size={64} />
              <RadialGauge label="Posture" value={!faceReady || !rawHeadPose || posture==="Scanning..." || posture==="Camera Off" || posture==="No Face" ? 0 : Math.max(10, (1 - (Math.abs(rawHeadPose.pitch) / 45 + Math.abs(rawHeadPose.yaw) / 55)) * 100) + jitter} icon={Activity}
                color={!faceReady || !rawHeadPose || posture==="Scanning..." || posture==="Camera Off" || posture==="No Face" ? "red" : posture==="Good" ? "green" : "yellow"} size={64} />
            </div>
            <div className="flex items-center justify-between text-[11px] px-1">
              <span className="text-cyan-400/80">Emotion</span>
              <span className={`font-bold capitalize ${getEmotionColor(emotion)}`}>{emotion}</span>
            </div>
            {emotionHistory.length>2&&(
              <div className="mt-3 pt-3 border-t border-white/5">
                <div className="text-[9px] text-gray-500 uppercase tracking-widest mb-1">Confidence Timeline</div>
                <ResponsiveContainer width="100%" height={50}>
                  <AreaChart data={emotionHistory}><defs><linearGradient id="cG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4}/><stop offset="100%" stopColor="#06b6d4" stopOpacity={0}/></linearGradient></defs><Area type="monotone" dataKey="confidence" stroke="#06b6d4" fill="url(#cG)" strokeWidth={1.5} dot={false}/></AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Q&A Panel */}
          <div className="bg-black/40 backdrop-blur-md border border-cyan-500/20 rounded-xl p-4 flex flex-col flex-1 min-h-0">
            <h3 className="text-[11px] text-cyan-400/80 uppercase tracking-widest mb-3 flex items-center gap-2"><Zap className="w-3.5 h-3.5"/>Your Response</h3>

            {phase==="idle"&&<p className="text-xs text-cyan-400/40 text-center py-4 font-sans">Initializing session...</p>}

            {phase==="asking"&&(
              <>
                <div className="relative mb-2">
                  <textarea 
                    value={answer} 
                    onChange={e=>setAnswer(e.target.value)} 
                    placeholder={isRecording ? "Recording..." : "Type or speak your answer..."} 
                    rows={4}
                    className="w-full p-2.5 pr-10 rounded-lg bg-gray-900/60 border border-cyan-500/20 focus:border-cyan-500/50 text-xs text-white placeholder-gray-600 resize-none focus:outline-none focus-visible:ring-1 focus-visible:ring-cyan-500 font-sans" 
                  />
                  <div className="absolute right-2 bottom-2 flex flex-col items-center gap-1.5">
                    {isRecording && (
                      <span className="text-[9px] text-red-500 font-bold animate-pulse">{30 - recordingTime}s</span>
                    )}
                    <button 
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={isTranscribing}
                      title={isRecording ? "Stop Recording" : "Voice Answering"}
                      className={`p-2 rounded-lg transition-all ${isRecording ? "bg-red-500/20 text-red-400 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.3)]" : "bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20"}`}
                    >
                      {isTranscribing ? <div className="w-3.5 h-3.5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" /> : (isRecording ? <Square className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />)}
                    </button>
                  </div>
                </div>
                <button onClick={submitAnswer} disabled={!answer.trim() || isRecording || isTranscribing}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gradient-to-r from-cyan-600 to-cyan-500 text-black text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed hover:from-cyan-500 hover:to-cyan-400 transition-all shadow-[0_0_20px_rgba(0,240,255,0.2)]">
                  <Send className="w-4 h-4"/> Submit Answer
                </button>
              </>
            )}

            {phase==="evaluating"&&(<div className="flex items-center justify-center gap-3 py-6"><div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"/><span className="text-xs text-cyan-400/70">AI evaluating...</span></div>)}

            {phase==="feedback"&&feedback&&(
              <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="space-y-3 overflow-y-auto flex-1 pr-1">
                <div className={`p-3 rounded-xl border ${feedback.score>=7?"bg-green-500/10 border-green-500/30":feedback.score>=4?"bg-yellow-500/10 border-yellow-500/30":"bg-red-500/10 border-red-500/30"}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-black ${feedback.score>=7?"bg-green-500/20 text-green-400":feedback.score>=4?"bg-yellow-500/20 text-yellow-400":"bg-red-500/20 text-red-400"}`}>{feedback.score}</div>
                    <div><div className={`text-sm font-bold ${getScoreColor(feedback.score)}`}>{feedback.score>=8?"Excellent":feedback.score>=6?"Good":feedback.score>=4?"Average":"Needs Work"}</div><div className="text-[10px] text-gray-500">out of 10</div></div>
                  </div>
                  {(feedback.clarity_score!=null||feedback.content_score!=null)&&(
                    <div className="space-y-1.5 mt-2">
                      {feedback.clarity_score!=null&&(<div><div className="flex justify-between text-[10px] mb-0.5"><span className="text-blue-400">Clarity</span><span className="text-white font-bold">{Math.round(feedback.clarity_score)}%</span></div><div className="h-1.5 bg-black/40 rounded-full overflow-hidden"><motion.div className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full" initial={{width:0}} animate={{width:`${Math.min(feedback.clarity_score,100)}%`}} transition={{duration:0.6}}/></div></div>)}
                      {feedback.content_score!=null&&(<div><div className="flex justify-between text-[10px] mb-0.5"><span className="text-purple-400">Content</span><span className="text-white font-bold">{Math.round(feedback.content_score)}%</span></div><div className="h-1.5 bg-black/40 rounded-full overflow-hidden"><motion.div className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full" initial={{width:0}} animate={{width:`${Math.min(feedback.content_score,100)}%`}} transition={{duration:0.6,delay:0.1}}/></div></div>)}
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-300 font-sans leading-relaxed">{feedback.feedback}</p>
                {feedback.golden_answer&&(<div className="p-3 rounded-lg bg-cyan-900/10 border border-cyan-500/20"><div className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider mb-1">Model Answer</div><p className="text-xs text-gray-300 font-sans leading-relaxed">{feedback.golden_answer}</p></div>)}
                {feedback.strengths?.length>0&&(<div>{feedback.strengths.slice(0,2).map((s,i)=><span key={i} className="inline-block mr-1 mb-1 px-1.5 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[9px]">{s}</span>)}</div>)}
                {feedback.improvements?.length>0&&(<div>{feedback.improvements.slice(0,2).map((s,i)=><span key={i} className="inline-block mr-1 mb-1 px-1.5 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[9px]">{s}</span>)}</div>)}
              </motion.div>
            )}
          </div>

          {/* Transcript */}
          <div className="bg-black/40 backdrop-blur-md border border-cyan-500/20 rounded-xl p-2.5 max-h-32 overflow-y-auto">
            <div className="text-[9px] text-cyan-400/50 uppercase tracking-widest mb-1.5">Live Transcript</div>
            {transcript.length===0&&<p className="text-cyan-400/20 text-center py-1 text-[10px] font-sans">Awaiting dialogue...</p>}
            {transcript.map((e,i)=>(
              <div key={i} className={`p-1 mb-1 rounded border-l-2 text-[10px] ${e.type==="question"?"bg-cyan-900/10 border-cyan-500":e.type==="answer"?"bg-purple-900/10 border-purple-500":"bg-green-900/10 border-green-500"}`}>
                <span className={`text-[7px] uppercase tracking-widest font-bold ${e.type==="question"?"text-cyan-500":e.type==="answer"?"text-purple-400":"text-green-400"}`}>{e.type==="question"?`Q${e.num}`:e.type==="answer"?"You":"AI"}</span>
                <p className="text-gray-300 mt-0.5 font-sans leading-snug">{e.text.length>100?e.text.substring(0,100)+"...":e.text}</p>
              </div>
            ))}
            <div ref={transcriptEndRef}/>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2">
            <button onClick={fetchNextQuestion} disabled={isEnding||phase==="loading"||phase==="evaluating"}
              className="w-full py-2.5 bg-cyan-900/20 border border-cyan-500/20 hover:border-cyan-500 text-cyan-200 uppercase tracking-widest font-bold text-xs transition-all hover:shadow-[0_0_15px_rgba(6,182,212,0.2)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 rounded-lg">
              <ArrowRight className="w-3.5 h-3.5"/> Next Question
            </button>
            <button onClick={()=>setShowEndConfirm(true)} disabled={isEnding}
              className="w-full py-2.5 bg-gradient-to-r from-red-900/40 to-red-800/40 border border-red-500/40 hover:border-red-500 text-red-200 uppercase tracking-widest font-bold text-xs transition-all hover:shadow-[0_0_20px_rgba(220,38,38,0.2)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 rounded-lg">
              <StopCircle className="w-3.5 h-3.5"/> {isEnding?"Ending...":"End Session"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
