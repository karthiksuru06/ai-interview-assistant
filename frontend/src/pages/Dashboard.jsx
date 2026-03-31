import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code2,
  Users,
  Database,
  Briefcase,
  Brain,
  GraduationCap,
  Play,
  LogOut,
  ChevronRight,
  Sparkles,
  History,
  BookOpen,
  Cpu,
  Zap,
  Activity,
  Shield,
} from "lucide-react";

const SUBJECTS = [
  { id: "software-engineering", name: "Software Engineering", icon: Code2, color: "#3b82f6", description: "System design, algorithms, clean code, and engineering best practices" },
  { id: "python", name: "Python", icon: Code2, color: "#3b82f6", description: "Decorators, generators, memory management, and GIL" },
  { id: "java", name: "Java", icon: Code2, color: "#f59e0b", description: "JVM internals, multi-threading, OOPs, and garbage collection" },
  { id: "react", name: "React", icon: Cpu, color: "#06b6d4", description: "Virtual DOM, hooks, state management, and performance" },
  { id: "data-science", name: "Data Science", icon: Database, color: "#10b981", description: "Statistics, data cleaning, visualization, and hypothesis testing" },
  { id: "machine-learning", name: "Machine Learning", icon: Brain, color: "#8b5cf6", description: "Supervised/unsupervised learning, neural networks, and model evaluation" },
  { id: "hr", name: "HR / Behavioral", icon: Users, color: "#ec4899", description: "Leadership, conflict resolution, and soft skills" },
  { id: "product-management", name: "Product Management", icon: Briefcase, color: "#f97316", description: "Prioritization, roadmap, KPIs, and user-centric design" },
  { id: "os", name: "Operating Systems", icon: Shield, color: "#ef4444", description: "Process scheduling, deadlock, and memory management" },
  { id: "networks", name: "Computer Networks", icon: Activity, color: "#6366f1", description: "OSI model, TCP/UDP, DNS, and network security" },
  { id: "sql", name: "SQL Databases", icon: Database, color: "#7c3aed", description: "ACID properties, joins, transactions, and normalization" },
];

const DIFFICULTIES = [
  { id: "easy", name: "Easy", color: "#22c55e", description: "Basic concepts and introductory questions" },
  { id: "medium", name: "Medium", color: "#f59e0b", description: "Intermediate level, industry standard" },
  { id: "hard", name: "Hard", color: "#ef4444", description: "Advanced concepts, FAANG-level difficulty" },
];

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
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  logoIcon: {
    width: 38,
    height: 38,
    borderRadius: 10,
    background: "linear-gradient(135deg, #7c3aed, #5b21b6)",
    boxShadow: "0 0 15px rgba(124,58,237,0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontWeight: 800,
    fontSize: 13,
  },
  logoText: {
    fontSize: 18,
    fontWeight: 700,
    color: "#fff",
  },
  navLinks: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  navLink: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 14px",
    borderRadius: 8,
    border: "none",
    background: "rgba(255,255,255,0.04)",
    color: "#9aa6b2",
    fontSize: 13,
    cursor: "pointer",
    transition: "all 0.2s",
    textDecoration: "none",
  },
  userSection: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  userName: {
    color: "#7a8490",
    fontSize: 13,
  },
  logoutBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 14px",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    color: "#9aa6b2",
    fontSize: 13,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  main: {
    maxWidth: 1200,
    margin: "0 auto",
    padding: "48px 32px",
    position: "relative",
    zIndex: 1,
  },
  header: {
    textAlign: "center",
    marginBottom: 48,
  },
  title: {
    fontSize: 36,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 12,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 16,
    color: "#7a8490",
    maxWidth: 500,
    margin: "0 auto",
    lineHeight: 1.5,
  },
  section: {
    marginBottom: 48,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: "#fff",
    marginBottom: 20,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  subjectGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
    gap: 14,
  },
  subjectCard: {
    padding: 20,
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.05)",
    background: "rgba(255,255,255,0.02)",
    backdropFilter: "blur(10px)",
    cursor: "pointer",
    transition: "all 0.3s",
    display: "flex",
    gap: 16,
    alignItems: "flex-start",
    position: "relative",
    overflow: "hidden",
  },
  subjectCardSelected: {
    borderColor: "rgba(124,58,237,0.4)",
    background: "rgba(124,58,237,0.08)",
    boxShadow: "0 0 30px rgba(124,58,237,0.1), inset 0 1px 0 rgba(255,255,255,0.05)",
  },
  subjectIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  subjectInfo: {
    flex: 1,
  },
  subjectName: {
    fontSize: 16,
    fontWeight: 600,
    color: "#fff",
    marginBottom: 4,
  },
  subjectDesc: {
    fontSize: 13,
    color: "#7a8490",
    lineHeight: 1.5,
  },
  difficultyRow: {
    display: "flex",
    gap: 14,
  },
  difficultyCard: {
    flex: 1,
    padding: 22,
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.05)",
    background: "rgba(255,255,255,0.02)",
    backdropFilter: "blur(10px)",
    cursor: "pointer",
    transition: "all 0.3s",
    textAlign: "center",
    position: "relative",
    overflow: "hidden",
  },
  difficultySelected: {
    borderColor: "rgba(124,58,237,0.4)",
    background: "rgba(124,58,237,0.08)",
    boxShadow: "0 0 30px rgba(124,58,237,0.1), inset 0 1px 0 rgba(255,255,255,0.05)",
  },
  difficultyName: {
    fontSize: 16,
    fontWeight: 600,
    color: "#fff",
    marginBottom: 6,
  },
  difficultyDesc: {
    fontSize: 12,
    color: "#7a8490",
  },
  difficultyDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    margin: "0 auto 12px",
    boxShadow: "0 0 10px currentColor",
  },
  startSection: {
    textAlign: "center",
    padding: "40px 0",
  },
  startButton: {
    display: "inline-flex",
    alignItems: "center",
    gap: 12,
    padding: "18px 52px",
    borderRadius: 14,
    border: "none",
    background: "linear-gradient(135deg, #9333ea, #7c3aed, #2563eb)",
    color: "#fff",
    fontSize: 18,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.3s",
    boxShadow: "0 8px 32px rgba(124,58,237,0.4), 0 0 60px rgba(37,99,235,0.15)",
    position: "relative",
    overflow: "hidden",
  },
  startButtonDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
    boxShadow: "none",
  },
  selectionSummary: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    marginTop: 24,
    color: "#7a8490",
    fontSize: 14,
  },
  summaryItem: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  badge: {
    padding: "4px 12px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 500,
    backdropFilter: "blur(10px)",
  },
};

/* ───── Animation variants ───── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 15, scale: 0.97 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: "easeOut" } },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState("medium");

  const handleStart = () => {
    if (!selectedSubject) return;
    navigate("/session", {
      state: {
        subject: selectedSubject,
        difficulty: selectedDifficulty,
      },
    });
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const selectedSubjectData = SUBJECTS.find((s) => s.id === selectedSubject);
  const selectedDifficultyData = DIFFICULTIES.find((d) => d.id === selectedDifficulty);

  return (
    <div style={styles.container}>
      {/* Background orbs */}
      <FloatingOrb size={400} color="#7c3aed" top="-10%" left="-5%" delay={0} />
      <FloatingOrb size={300} color="#3b82f6" top="50%" left="80%" delay={2} />
      <FloatingOrb size={250} color="#ec4899" top="80%" left="20%" delay={4} />

      {/* Navbar */}
      <motion.nav
        style={styles.navbar}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div style={styles.logo}>
          <motion.div
            style={styles.logoIcon}
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ duration: 0.2 }}
          >
            SA
          </motion.div>
          <span style={styles.logoText}>Smart AI</span>
        </div>

        <div style={styles.navLinks}>
          <button
            style={styles.navLink}
            onClick={() => navigate("/history")}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#fff"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.color = "#9aa6b2"; }}
          >
            <History size={15} />
            History
          </button>
          <button
            style={styles.navLink}
            onClick={() => navigate("/question-bank")}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#fff"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.color = "#9aa6b2"; }}
          >
            <BookOpen size={15} />
            Questions
          </button>
        </div>

        <div style={styles.userSection}>
          <span style={styles.userName}>Welcome, {user?.username || "User"}</span>
          <button
            style={styles.logoutBtn}
            onClick={handleLogout}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(239,68,68,0.3)"; e.currentTarget.style.color = "#f87171"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)"; e.currentTarget.style.color = "#9aa6b2"; }}
          >
            <LogOut size={15} />
            Sign Out
          </button>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main style={styles.main}>
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.header style={styles.header} variants={itemVariants}>
            <h1 style={styles.title}>Prepare for Your Interview</h1>
            <p style={styles.subtitle}>
              Select a subject and difficulty level to start your AI-powered mock interview session
            </p>
          </motion.header>

          {/* Subject Selection */}
          <motion.section style={styles.section} variants={itemVariants}>
            <h2 style={styles.sectionTitle}>
              <Sparkles size={20} color="#7c3aed" />
              Choose Your Subject
            </h2>
            <div style={styles.subjectGrid}>
              {SUBJECTS.map((subject, index) => {
                const Icon = subject.icon;
                const isSelected = selectedSubject === subject.id;
                return (
                  <motion.div
                    key={subject.id}
                    variants={cardVariants}
                    style={{
                      ...styles.subjectCard,
                      ...(isSelected ? styles.subjectCardSelected : {}),
                    }}
                    onClick={() => setSelectedSubject(subject.id)}
                    whileHover={{
                      scale: 1.02,
                      borderColor: isSelected ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.12)",
                      background: isSelected ? "rgba(124,58,237,0.12)" : "rgba(255,255,255,0.04)",
                    }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div
                      style={{
                        ...styles.subjectIcon,
                        background: `${subject.color}15`,
                      }}
                    >
                      <Icon size={24} color={subject.color} />
                    </div>
                    <div style={styles.subjectInfo}>
                      <div style={styles.subjectName}>{subject.name}</div>
                      <div style={styles.subjectDesc}>{subject.description}</div>
                    </div>
                    <AnimatePresence>
                      {isSelected && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0 }}
                        >
                          <ChevronRight size={20} color="#7c3aed" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          </motion.section>

          {/* Difficulty Selection */}
          <motion.section style={styles.section} variants={itemVariants}>
            <h2 style={styles.sectionTitle}>
              <Sparkles size={20} color="#7c3aed" />
              Select Difficulty
            </h2>
            <div style={styles.difficultyRow}>
              {DIFFICULTIES.map((diff) => {
                const isSelected = selectedDifficulty === diff.id;
                return (
                  <motion.div
                    key={diff.id}
                    variants={cardVariants}
                    style={{
                      ...styles.difficultyCard,
                      ...(isSelected ? styles.difficultySelected : {}),
                    }}
                    onClick={() => setSelectedDifficulty(diff.id)}
                    whileHover={{
                      scale: 1.03,
                      borderColor: isSelected ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.12)",
                    }}
                    whileTap={{ scale: 0.97 }}
                  >
                    <motion.div
                      style={{ ...styles.difficultyDot, background: diff.color, color: diff.color }}
                      animate={isSelected ? { scale: [1, 1.3, 1] } : {}}
                      transition={{ duration: 0.5 }}
                    />
                    <div style={styles.difficultyName}>{diff.name}</div>
                    <div style={styles.difficultyDesc}>{diff.description}</div>
                  </motion.div>
                );
              })}
            </div>
          </motion.section>

          {/* Start Button */}
          <motion.div style={styles.startSection} variants={itemVariants}>
            <motion.button
              style={{
                ...styles.startButton,
                ...(selectedSubject ? {} : styles.startButtonDisabled),
              }}
              onClick={handleStart}
              disabled={!selectedSubject}
              whileHover={selectedSubject ? {
                scale: 1.05,
                boxShadow: "0 12px 40px rgba(124,58,237,0.5), 0 0 80px rgba(37,99,235,0.2)",
              } : {}}
              whileTap={selectedSubject ? { scale: 0.97 } : {}}
            >
              <Play size={22} />
              Start Interview Session
              <Sparkles size={16} style={{ opacity: 0.6 }} />
            </motion.button>

            <AnimatePresence>
              {selectedSubject && selectedSubjectData && selectedDifficultyData && (
                <motion.div
                  style={styles.selectionSummary}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                >
                  <div style={styles.summaryItem}>
                    <span>Subject:</span>
                    <span
                      style={{
                        ...styles.badge,
                        background: `${selectedSubjectData.color}18`,
                        color: selectedSubjectData.color,
                        border: `1px solid ${selectedSubjectData.color}30`,
                      }}
                    >
                      {selectedSubjectData.name}
                    </span>
                  </div>
                  <div style={styles.summaryItem}>
                    <span>Difficulty:</span>
                    <span
                      style={{
                        ...styles.badge,
                        background: `${selectedDifficultyData.color}18`,
                        color: selectedDifficultyData.color,
                        border: `1px solid ${selectedDifficultyData.color}30`,
                      }}
                    >
                      {selectedDifficultyData.name}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
}
