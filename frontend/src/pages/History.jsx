import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import jsPDF from "jspdf";
import "jspdf-autotable";
import {
  Download,
  Calendar,
  Clock,
  Star,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Loader2,
  FileText,
  TrendingUp,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

/* ───── Floating background orb ───── */
const FloatingOrb = ({ size, color, top, left, delay }) => (
  <motion.div
    animate={{
      y: [0, -25, 0],
      x: [0, 12, 0],
      scale: [1, 1.08, 1],
    }}
    transition={{ duration: 10, repeat: Infinity, delay, ease: "easeInOut" }}
    style={{
      position: "fixed",
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      top,
      left,
      filter: "blur(100px)",
      opacity: 0.15,
      pointerEvents: "none",
      zIndex: 0,
    }}
  />
);

const styles = {
  container: {
    minHeight: "100vh",
    background: "#0a0a0f",
    color: "#e6eef8",
    position: "relative",
    overflow: "hidden",
  },
  navbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 32px",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
    background: "rgba(10,10,15,0.8)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  backBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    color: "#9aa6b2",
    fontSize: 14,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  main: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "40px 32px",
    position: "relative",
    zIndex: 1,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 8,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 15,
    color: "#7a8490",
  },
  statsRow: {
    display: "flex",
    gap: 16,
    marginBottom: 32,
  },
  statCard: {
    flex: 1,
    padding: 20,
    borderRadius: 16,
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
  },
  statLabel: {
    fontSize: 12,
    color: "#7a8490",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: 4,
  },
  statValue: {
    fontSize: 28,
    fontWeight: 700,
    color: "#fff",
  },
  sessionCard: {
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 16,
    overflow: "hidden",
    marginBottom: 14,
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
    transition: "border-color 0.3s",
  },
  sessionHeader: {
    padding: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    cursor: "pointer",
    transition: "background 0.2s",
  },
  scoreBadge: {
    width: 50,
    height: 50,
    borderRadius: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 16,
  },
  pdfButton: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 16px",
    borderRadius: 10,
    border: "none",
    background: "linear-gradient(135deg, #7c3aed, #5b21b6)",
    color: "#fff",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
    boxShadow: "0 4px 12px rgba(124,58,237,0.3)",
  },
  expandedArea: {
    borderTop: "1px solid rgba(255,255,255,0.05)",
    background: "rgba(0,0,0,0.2)",
  },
  questionRow: {
    padding: 16,
    margin: "0 20px 12px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(255,255,255,0.05)",
  },
  loading: {
    textAlign: "center",
    padding: 60,
  },
  empty: {
    textAlign: "center",
    padding: 60,
    color: "#7a8490",
  },
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
};

function getScoreStyle(score) {
  if (score >= 7) return { background: "rgba(34,197,94,0.12)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.25)" };
  if (score >= 4) return { background: "rgba(245,158,11,0.12)", color: "#fbbf24", border: "1px solid rgba(245,158,11,0.25)" };
  return { background: "rgba(239,68,68,0.12)", color: "#f87171", border: "1px solid rgba(239,68,68,0.25)" };
}

export default function History() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    async function fetchHistory() {
      if (!user?.id) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.get(`/history/user/${user.id}`);
        setSessions(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        if (err.response?.status === 404) {
          setSessions([]);
        } else {
          setError(err.response?.data?.detail || "Failed to load history");
        }
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [user]);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const avgScore = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + (s.overall_score || 0), 0) / sessions.length).toFixed(1)
    : "—";

  const generatePDF = (session) => {
    const doc = new jsPDF();
    doc.setFontSize(22);
    doc.setTextColor(40, 40, 40);
    doc.text("Interview Performance Report", 14, 20);
    doc.setFontSize(12);
    doc.setTextColor(100, 100, 100);
    doc.text(`Role: ${session.job_role || session.subject || "Interview"}`, 14, 30);
    doc.text(`Difficulty: ${session.difficulty || "Medium"}`, 14, 36);
    doc.text(`Overall Score: ${session.overall_score || "N/A"}`, 14, 42);
    doc.setDrawColor(200, 200, 200);
    doc.line(14, 48, 196, 48);

    const questions = session.questions || session.qa_pairs || [];
    if (questions.length > 0) {
      const tableColumn = ["Question", "Answer", "Feedback", "Score"];
      const tableRows = questions.map((q) => [
        q.question_text || q.q || "",
        q.user_response || q.answer_text || q.a || "",
        q.ai_feedback || q.feedback || q.f || "",
        q.ai_score != null ? `${q.ai_score}/10` : q.score != null ? `${q.score}/10` : "—",
      ]);

      doc.autoTable({
        head: [tableColumn],
        body: tableRows,
        startY: 55,
        theme: "grid",
        headStyles: { fillColor: [124, 58, 237], textColor: 255 },
        styles: { fontSize: 10, cellPadding: 3 },
        columnStyles: {
          0: { cellWidth: 40 },
          1: { cellWidth: 50 },
          2: { cellWidth: 50 },
          3: { cellWidth: 20, halign: "center" },
        },
      });
    }

    doc.save(`Interview_Report_${session.job_role || "Session"}.pdf`);
  };

  return (
    <div style={styles.container}>
      <FloatingOrb size={350} color="#7c3aed" top="-5%" left="-3%" delay={0} />
      <FloatingOrb size={250} color="#3b82f6" top="60%" left="80%" delay={2} />
      <FloatingOrb size={200} color="#ec4899" top="80%" left="15%" delay={4} />

      {/* Navbar */}
      <nav style={styles.navbar}>
        <motion.button
          style={styles.backBtn}
          onClick={() => navigate("/dashboard")}
          whileHover={{ scale: 1.03, borderColor: "rgba(124,58,237,0.3)", color: "#fff" }}
          whileTap={{ scale: 0.97 }}
        >
          <ArrowLeft size={16} />
          Back to Dashboard
        </motion.button>
        <span style={{ fontSize: 16, fontWeight: 600, color: "#fff" }}>Interview History</span>
        <div style={{ width: 150 }} />
      </nav>

      <main style={styles.main}>
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          {/* Header */}
          <motion.div style={styles.header} variants={itemVariants}>
            <h1 style={styles.title}>Your Interview History</h1>
            <p style={styles.subtitle}>Track your progress and download detailed reports</p>
          </motion.div>

          {/* Stats */}
          <motion.div style={styles.statsRow} variants={itemVariants}>
            <div style={styles.statCard}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FileText size={16} color="#7c3aed" />
                <span style={styles.statLabel}>Total Sessions</span>
              </div>
              <div style={styles.statValue}>{sessions.length}</div>
            </div>
            <div style={styles.statCard}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <TrendingUp size={16} color="#22c55e" />
                <span style={styles.statLabel}>Average Score</span>
              </div>
              <div style={{ ...styles.statValue, color: "#4ade80" }}>{avgScore}</div>
            </div>
          </motion.div>

          {/* Loading */}
          {loading && (
            <div style={styles.loading}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                style={{ display: "inline-block" }}
              >
                <Loader2 size={32} color="#7c3aed" />
              </motion.div>
              <p style={{ color: "#7a8490", marginTop: 16 }}>Loading your history...</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              textAlign: "center", padding: 40,
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: 16, color: "#f87171",
            }}>
              {error}
            </div>
          )}

          {/* Empty */}
          {!loading && !error && sessions.length === 0 && (
            <motion.div style={styles.empty} variants={itemVariants}>
              <FileText size={48} color="#7a8490" style={{ marginBottom: 16, opacity: 0.5 }} />
              <p style={{ fontSize: 18, color: "#fff", marginBottom: 8 }}>No interviews yet</p>
              <p>Complete your first interview session to see your history here.</p>
              <motion.button
                style={{
                  marginTop: 20, padding: "12px 28px", borderRadius: 12, border: "none",
                  background: "linear-gradient(135deg, #7c3aed, #5b21b6)", color: "#fff",
                  fontSize: 15, fontWeight: 600, cursor: "pointer",
                  boxShadow: "0 4px 20px rgba(124,58,237,0.35)",
                }}
                onClick={() => navigate("/dashboard")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
              >
                Start an Interview
              </motion.button>
            </motion.div>
          )}

          {/* Session List */}
          {!loading && sessions.map((session, idx) => {
            const score = session.overall_score || 0;
            const scoreStyle = getScoreStyle(score);
            const sessionId = session.id || idx;
            const questions = session.questions || session.qa_pairs || [];

            return (
              <motion.div
                key={sessionId}
                variants={itemVariants}
                style={{
                  ...styles.sessionCard,
                  borderColor: expandedId === sessionId ? "rgba(124,58,237,0.3)" : "rgba(255,255,255,0.07)",
                }}
              >
                <div
                  style={styles.sessionHeader}
                  onClick={() => toggleExpand(sessionId)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                    <div style={{ ...styles.scoreBadge, ...scoreStyle }}>
                      {score}
                    </div>
                    <div>
                      <h3 style={{ fontSize: 17, fontWeight: 600, color: "#fff", marginBottom: 4 }}>
                        {session.job_role || session.subject || "Interview Session"}
                      </h3>
                      <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 13, color: "#7a8490" }}>
                        {session.difficulty && (
                          <span style={{
                            padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                            background: session.difficulty === "hard" ? "rgba(239,68,68,0.12)" :
                              session.difficulty === "easy" ? "rgba(34,197,94,0.12)" : "rgba(245,158,11,0.12)",
                            color: session.difficulty === "hard" ? "#f87171" :
                              session.difficulty === "easy" ? "#4ade80" : "#fbbf24",
                          }}>
                            {session.difficulty.charAt(0).toUpperCase() + session.difficulty.slice(1)}
                          </span>
                        )}
                        {session.created_at && (
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <Calendar size={12} />
                            {new Date(session.created_at).toLocaleDateString()}
                          </span>
                        )}
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <Clock size={12} />
                          {questions.length} questions
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <motion.button
                      style={styles.pdfButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        generatePDF(session);
                      }}
                      whileHover={{ scale: 1.05, boxShadow: "0 6px 20px rgba(124,58,237,0.4)" }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Download size={14} /> PDF
                    </motion.button>
                    {expandedId === sessionId
                      ? <ChevronUp size={20} color="#7a8490" />
                      : <ChevronDown size={20} color="#7a8490" />
                    }
                  </div>
                </div>

                <AnimatePresence>
                  {expandedId === sessionId && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      style={styles.expandedArea}
                    >
                      <div style={{ padding: "16px 20px" }}>
                        {questions.length === 0 && (
                          <p style={{ textAlign: "center", color: "#7a8490", padding: 20 }}>
                            No detailed question data available for this session.
                          </p>
                        )}
                        {questions.map((q, qIdx) => {
                          const qScore = q.ai_score ?? q.score;
                          const qAnswer = q.user_response || q.answer_text || q.a || "—";
                          const qFeedback = q.ai_feedback || q.feedback || q.f;
                          return (
                          <div key={qIdx} style={styles.questionRow}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                              <h4 style={{ fontSize: 14, fontWeight: 600, color: "#e6eef8", flex: 1 }}>
                                Q{qIdx + 1}: {q.question_text || q.q || "—"}
                              </h4>
                              {qScore != null && (
                                <span style={{
                                  padding: "2px 10px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                                  ...getScoreStyle(qScore),
                                }}>
                                  {qScore}/10
                                </span>
                              )}
                            </div>
                            <p style={{ fontSize: 13, color: "#9aa6b2", marginBottom: 6 }}>
                              <strong style={{ color: "#7a8490" }}>Answer:</strong> {qAnswer}
                            </p>
                            {qFeedback && (
                              <div style={{
                                display: "flex", alignItems: "flex-start", gap: 8,
                                padding: 10, borderRadius: 8,
                                background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.15)",
                              }}>
                                <Star size={14} color="#4ade80" style={{ marginTop: 2, flexShrink: 0 }} />
                                <span style={{ fontSize: 13, color: "#4ade80" }}>
                                  {qFeedback}
                                </span>
                              </div>
                            )}
                          </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>
      </main>
    </div>
  );
}
