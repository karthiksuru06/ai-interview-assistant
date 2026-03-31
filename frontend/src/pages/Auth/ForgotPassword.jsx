import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, KeyRound, Loader2, CheckCircle, Mail, ShieldQuestion, Lock } from "lucide-react";

const styles = {
  container: {
    minHeight: "100vh",
    background: "#0a0a0f",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    position: "relative",
    overflow: "hidden",
  },
  card: {
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(40px) saturate(1.5)",
    WebkitBackdropFilter: "blur(40px) saturate(1.5)",
    borderRadius: 24,
    border: "1px solid rgba(255,255,255,0.08)",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
    padding: 40,
    width: "100%",
    maxWidth: 440,
    position: "relative",
    zIndex: 2,
  },
  backLink: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    color: "#9aa6b2",
    textDecoration: "none",
    fontSize: 14,
    marginBottom: 24,
    transition: "color 0.2s",
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 8,
  },
  subtitle: {
    color: "#9aa6b2",
    fontSize: 14,
    marginBottom: 28,
    lineHeight: 1.5,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "#9aa6b2",
  },
  input: {
    width: "100%",
    padding: "12px 16px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(10px)",
    color: "#fff",
    fontSize: 14,
    outline: "none",
    boxSizing: "border-box",
    transition: "border-color 0.3s, box-shadow 0.3s",
  },
  questionBox: {
    background: "rgba(124,58,237,0.08)",
    border: "1px solid rgba(124,58,237,0.2)",
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
  },
  questionLabel: {
    fontSize: 12,
    color: "#a78bfa",
    marginBottom: 4,
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  questionText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: 500,
  },
  button: {
    padding: "14px 24px",
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #7c3aed, #5b21b6)",
    color: "#fff",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    transition: "opacity 0.2s, transform 0.2s, box-shadow 0.2s",
    boxShadow: "0 4px 15px rgba(124,58,237,0.3)",
  },
  error: {
    background: "rgba(239,68,68,0.08)",
    border: "1px solid rgba(239,68,68,0.2)",
    borderRadius: 10,
    padding: 12,
    color: "#f87171",
    fontSize: 13,
    textAlign: "center",
  },
  success: {
    textAlign: "center",
    padding: 20,
  },
  successIcon: {
    width: 72,
    height: 72,
    borderRadius: 36,
    background: "rgba(34,197,94,0.1)",
    border: "1px solid rgba(34,197,94,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 16px",
  },
  successTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 8,
  },
  successText: {
    color: "#9aa6b2",
    fontSize: 14,
    marginBottom: 24,
    lineHeight: 1.5,
  },
  stepIndicator: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginBottom: 24,
  },
  step: {
    width: 36,
    height: 36,
    borderRadius: 18,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 600,
    transition: "all 0.3s",
  },
  stepActive: {
    background: "linear-gradient(135deg, #7c3aed, #5b21b6)",
    color: "#fff",
    boxShadow: "0 0 15px rgba(124,58,237,0.4)",
  },
  stepInactive: {
    background: "rgba(255,255,255,0.06)",
    color: "#9aa6b2",
  },
  stepLine: {
    width: 40,
    height: 2,
    borderRadius: 1,
    background: "rgba(255,255,255,0.08)",
  },
};

const FloatingOrb = ({ size, color, top, left, delay }) => (
  <motion.div
    animate={{
      y: [0, -30, 0],
      x: [0, 15, 0],
      scale: [1, 1.1, 1],
    }}
    transition={{ duration: 6, repeat: Infinity, delay, ease: "easeInOut" }}
    style={{
      position: "absolute",
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      top,
      left,
      filter: "blur(60px)",
      opacity: 0.3,
      pointerEvents: "none",
    }}
  />
);

export default function ForgotPassword() {
  const navigate = useNavigate();
  const { getSecurityQuestion, resetPassword } = useAuth();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleFetchQuestion = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const question = await getSecurityQuestion(email);
      setSecurityQuestion(question);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || "No account found with that email");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      await resetPassword(email, securityAnswer, newPassword);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to reset password");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.container}>
        <FloatingOrb size={200} color="#22c55e" top="20%" left="10%" delay={0} />
        <FloatingOrb size={150} color="#7c3aed" top="60%" left="70%" delay={2} />
        <motion.div
          style={styles.card}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div style={styles.success}>
            <motion.div
              style={styles.successIcon}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", delay: 0.2 }}
            >
              <CheckCircle size={36} color="#22c55e" />
            </motion.div>
            <h2 style={styles.successTitle}>Password Reset!</h2>
            <p style={styles.successText}>
              Your password has been successfully reset. You can now sign in with your new password.
            </p>
            <Link to="/login" style={{ textDecoration: "none" }}>
              <button style={styles.button}>Go to Sign In</button>
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <FloatingOrb size={200} color="#7c3aed" top="10%" left="5%" delay={0} />
      <FloatingOrb size={160} color="#3b82f6" top="70%" left="80%" delay={1.5} />
      <FloatingOrb size={120} color="#ec4899" top="50%" left="20%" delay={3} />

      <motion.div
        style={styles.card}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <Link to="/login" style={styles.backLink}>
          <ArrowLeft size={18} />
          Back to Sign In
        </Link>

        <h1 style={styles.title}>Reset Password</h1>
        <p style={styles.subtitle}>
          {step === 1
            ? "Enter your email address to retrieve your security question"
            : "Answer your security question to set a new password"}
        </p>

        <div style={styles.stepIndicator}>
          <motion.div
            style={{ ...styles.step, ...(step >= 1 ? styles.stepActive : styles.stepInactive) }}
            animate={step >= 1 ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 0.3 }}
          >
            1
          </motion.div>
          <div style={styles.stepLine} />
          <motion.div
            style={{ ...styles.step, ...(step >= 2 ? styles.stepActive : styles.stepInactive) }}
            animate={step >= 2 ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 0.3 }}
          >
            2
          </motion.div>
        </div>

        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              key="error"
              style={styles.error}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.form
              key="step1"
              style={styles.form}
              onSubmit={handleFetchQuestion}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              <div style={styles.inputGroup}>
                <label style={styles.label}>
                  <Mail size={13} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  Email Address
                </label>
                <input
                  type="email"
                  style={styles.input}
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                style={{ ...styles.button, opacity: loading ? 0.7 : 1 }}
                disabled={loading}
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                {loading ? "Finding account..." : "Continue"}
              </button>
            </motion.form>
          ) : (
            <motion.form
              key="step2"
              style={styles.form}
              onSubmit={handleResetPassword}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              <div style={styles.questionBox}>
                <div style={styles.questionLabel}>
                  <ShieldQuestion size={13} />
                  Security Question
                </div>
                <div style={styles.questionText}>{securityQuestion}</div>
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label}>Your Answer</label>
                <input
                  type="text"
                  style={styles.input}
                  placeholder="Enter your answer"
                  value={securityAnswer}
                  onChange={(e) => setSecurityAnswer(e.target.value)}
                  required
                />
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label}>
                  <Lock size={13} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  New Password
                </label>
                <input
                  type="password"
                  style={styles.input}
                  placeholder="Min 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label}>Confirm New Password</label>
                <input
                  type="password"
                  style={styles.input}
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                style={{ ...styles.button, opacity: loading ? 0.7 : 1 }}
                disabled={loading}
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : <KeyRound size={18} />}
                {loading ? "Resetting..." : "Reset Password"}
              </button>
            </motion.form>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
