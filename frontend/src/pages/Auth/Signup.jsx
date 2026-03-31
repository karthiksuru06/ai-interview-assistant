import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, UserPlus, Loader2, Sparkles, ShieldCheck } from "lucide-react";

const SECURITY_QUESTIONS = [
  "What is your pet's name?",
  "What city were you born in?",
  "What is your mother's maiden name?",
  "What was the name of your first school?",
  "What is your favorite movie?",
  "What was your childhood nickname?",
];

/* ───── Floating background orb ───── */
const FloatingOrb = ({ size, color, top, left, delay }) => (
  <motion.div
    animate={{
      y: [0, -35, 0],
      x: [0, 18, 0],
      scale: [1, 1.12, 1],
    }}
    transition={{ duration: 7, repeat: Infinity, delay, ease: "easeInOut" }}
    style={{
      position: "absolute",
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      top,
      left,
      filter: "blur(80px)",
      opacity: 0.22,
      pointerEvents: "none",
    }}
  />
);

/* ───── Animated grid ───── */
const GridOverlay = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage:
        "linear-gradient(rgba(124,58,237,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.025) 1px, transparent 1px)",
      backgroundSize: "60px 60px",
      pointerEvents: "none",
      zIndex: 0,
    }}
  />
);

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
    background: "rgba(255, 255, 255, 0.03)",
    backdropFilter: "blur(40px) saturate(1.5)",
    WebkitBackdropFilter: "blur(40px) saturate(1.5)",
    borderRadius: 28,
    border: "1px solid rgba(255, 255, 255, 0.07)",
    boxShadow:
      "0 8px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.05), 0 0 80px rgba(124,58,237,0.05)",
    padding: "44px 48px",
    width: "100%",
    maxWidth: 520,
    position: "relative",
    zIndex: 2,
  },
  glassShine: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: "40%",
    borderRadius: "28px 28px 0 0",
    background: "linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%)",
    pointerEvents: "none",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    marginBottom: 32,
  },
  logoIcon: {
    width: 56,
    height: 56,
    borderRadius: 16,
    background: "linear-gradient(135deg, #8b5cf6, #3b82f6)",
    boxShadow: "0 0 25px rgba(139, 92, 246, 0.4), 0 0 60px rgba(59,130,246,0.15)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontWeight: 800,
    fontSize: 20,
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    color: "#fff",
    margin: 0,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    color: "#7a8490",
    fontSize: 14,
    textAlign: "center",
    marginBottom: 24,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  row: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 14,
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: 500,
    color: "#7a8490",
    letterSpacing: "0.03em",
    textTransform: "uppercase",
  },
  inputWrapper: {
    position: "relative",
  },
  input: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(10px)",
    color: "#fff",
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.3s, box-shadow 0.3s",
    boxSizing: "border-box",
  },
  select: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(0,0,0,0.4)",
    backdropFilter: "blur(10px)",
    color: "#fff",
    fontSize: 14,
    outline: "none",
    cursor: "pointer",
    boxSizing: "border-box",
    transition: "border-color 0.3s, box-shadow 0.3s",
  },
  eyeButton: {
    position: "absolute",
    right: 12,
    top: "50%",
    transform: "translateY(-50%)",
    background: "none",
    border: "none",
    color: "#7a8490",
    cursor: "pointer",
    padding: 4,
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
    marginTop: 6,
    transition: "all 0.3s",
    boxShadow: "0 4px 20px rgba(124,58,237,0.35), 0 0 40px rgba(124,58,237,0.1)",
    position: "relative",
    overflow: "hidden",
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
  links: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: 20,
  },
  linkText: {
    color: "#7a8490",
    fontSize: 14,
  },
  link: {
    color: "#7c3aed",
    textDecoration: "none",
    fontSize: 14,
    fontWeight: 500,
  },
  hint: {
    fontSize: 11,
    color: "#5a636e",
    marginTop: 2,
    display: "flex",
    alignItems: "center",
    gap: 4,
  },
  securitySection: {
    background: "rgba(124,58,237,0.04)",
    border: "1px solid rgba(124,58,237,0.1)",
    borderRadius: 14,
    padding: "14px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  securityHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13,
    fontWeight: 600,
    color: "#a78bfa",
  },
};

const inputFocusHandlers = {
  onFocus: (e) => {
    e.target.style.borderColor = "rgba(124,58,237,0.5)";
    e.target.style.boxShadow = "0 0 20px rgba(124,58,237,0.12)";
  },
  onBlur: (e) => {
    e.target.style.borderColor = "rgba(255,255,255,0.07)";
    e.target.style.boxShadow = "none";
  },
};

/* ───── Animation variants ───── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

export default function Signup() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    security_question: "",
    security_answer: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputId = React.useId();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (!/[A-Z]/.test(formData.password) || !/[a-z]/.test(formData.password) || !/\d/.test(formData.password)) {
      setError("Password must contain at least one uppercase letter, one lowercase letter, and one digit");
      return;
    }

    if (!formData.security_question) {
      setError("Please select a security question");
      return;
    }

    setLoading(true);

    try {
      await signup({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        security_question: formData.security_question,
        security_answer: formData.security_answer,
      });
      navigate("/dashboard");
    } catch (err) {
      console.error("[Signup] Error:", err);
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors — extract msg fields
        const messages = detail.map(e => e.msg || e.message || JSON.stringify(e));
        setError(messages.join(". "));
      } else if (detail && typeof detail === "object") {
        setError(detail.msg || detail.message || JSON.stringify(detail));
      } else if (err.response?.data?.msg) {
        setError(err.response.data.msg);
      } else if (err.message) {
        // Network error or other JS error
        setError(err.message === "Network Error"
          ? "Cannot connect to server. Make sure the backend is running on port 8000."
          : `Error: ${err.message}`
        );
      } else {
        setError("Signup failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Background effects */}
      <GridOverlay />
      <FloatingOrb size={300} color="#7c3aed" top="-10%" left="-10%" delay={0} />
      <FloatingOrb size={220} color="#3b82f6" top="60%" left="80%" delay={1.5} />
      <FloatingOrb size={180} color="#ec4899" top="75%" left="5%" delay={3} />
      <FloatingOrb size={140} color="#06b6d4" top="15%" left="85%" delay={4.5} />

      <motion.div
        style={styles.card}
        initial={{ opacity: 0, y: 40, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <div style={styles.glassShine} />

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Logo */}
          <motion.div style={styles.logo} variants={itemVariants}>
            <motion.div
              style={styles.logoIcon}
              whileHover={{ rotate: [0, -5, 5, 0], scale: 1.1 }}
              transition={{ duration: 0.5 }}
            >
              SA
            </motion.div>
            <h1 style={styles.title}>Smart AI</h1>
          </motion.div>

          <motion.p style={styles.subtitle} variants={itemVariants}>
            Create your account to get started
          </motion.p>

          <AnimatePresence>
            {error && (
              <motion.div
                style={styles.error}
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, y: -10, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          <form style={styles.form} onSubmit={handleSubmit}>
            {/* Username & Email row */}
            <motion.div style={styles.row} variants={itemVariants}>
              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`username-${inputId}`}>Username</label>
                <input
                  id={`username-${inputId}`}
                  type="text"
                  name="username"
                  style={styles.input}
                  placeholder="Choose a username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                  minLength={3}
                  autoComplete="username"
                  {...inputFocusHandlers}
                />
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`email-${inputId}`}>Email</label>
                <input
                  id={`email-${inputId}`}
                  type="email"
                  name="email"
                  style={styles.input}
                  placeholder="your@email.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  autoComplete="email"
                  {...inputFocusHandlers}
                />
              </div>
            </motion.div>

            {/* Password row */}
            <motion.div style={styles.row} variants={itemVariants}>
              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`password-${inputId}`}>Password</label>
                <div style={styles.inputWrapper}>
                  <input
                    id={`password-${inputId}`}
                    type={showPassword ? "text" : "password"}
                    name="password"
                    style={{ ...styles.input, paddingRight: 44 }}
                    placeholder="Min 8 characters"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    {...inputFocusHandlers}
                  />
                  <button
                    type="button"
                    style={styles.eyeButton}
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`confirm-${inputId}`}>Confirm Password</label>
                <input
                  id={`confirm-${inputId}`}
                  type="password"
                  name="confirmPassword"
                  style={styles.input}
                  placeholder="Confirm password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                  {...inputFocusHandlers}
                />
              </div>
            </motion.div>

            {/* Security Section */}
            <motion.div style={styles.securitySection} variants={itemVariants}>
              <div style={styles.securityHeader}>
                <ShieldCheck size={16} />
                Account Recovery
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`question-${inputId}`}>Security Question</label>
                <select
                  id={`question-${inputId}`}
                  name="security_question"
                  style={styles.select}
                  value={formData.security_question}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select a security question</option>
                  {SECURITY_QUESTIONS.map((q) => (
                    <option key={q} value={q}>
                      {q}
                    </option>
                  ))}
                </select>
                <p style={styles.hint}>
                  <ShieldCheck size={11} />
                  Used to recover your account if you forget your password
                </p>
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor={`answer-${inputId}`}>Security Answer</label>
                <input
                  id={`answer-${inputId}`}
                  type="text"
                  name="security_answer"
                  style={styles.input}
                  placeholder="Your answer"
                  value={formData.security_answer}
                  onChange={handleChange}
                  required
                  minLength={2}
                  {...inputFocusHandlers}
                />
              </div>
            </motion.div>

            {/* Submit */}
            <motion.div variants={itemVariants}>
              <motion.button
                type="submit"
                style={{ ...styles.button, opacity: loading ? 0.7 : 1 }}
                disabled={loading}
                whileHover={!loading ? { scale: 1.02, boxShadow: "0 6px 30px rgba(124,58,237,0.5), 0 0 60px rgba(124,58,237,0.15)" } : {}}
                whileTap={!loading ? { scale: 0.98 } : {}}
              >
                {loading ? (
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                    <Loader2 size={18} />
                  </motion.div>
                ) : (
                  <UserPlus size={18} />
                )}
                {loading ? "Creating account..." : "Create Account"}
                {!loading && <Sparkles size={14} style={{ opacity: 0.5 }} />}
              </motion.button>
            </motion.div>
          </form>

          <motion.div style={styles.links} variants={itemVariants}>
            <span style={styles.linkText}>Already have an account?</span>
            <Link to="/login" style={styles.link}>
              Sign In
            </Link>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
}
