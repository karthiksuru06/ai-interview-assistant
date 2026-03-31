import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, LogIn, Loader2, Sparkles } from "lucide-react";

/* ───── Floating background orb ───── */
const FloatingOrb = ({ size, color, top, left, delay }) => (
  <motion.div
    animate={{
      y: [0, -40, 0],
      x: [0, 20, 0],
      scale: [1, 1.15, 1],
    }}
    transition={{ duration: 8, repeat: Infinity, delay, ease: "easeInOut" }}
    style={{
      position: "absolute",
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      top,
      left,
      filter: "blur(80px)",
      opacity: 0.25,
      pointerEvents: "none",
    }}
  />
);

/* ───── Animated grid lines ───── */
const GridOverlay = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage:
        "linear-gradient(rgba(124,58,237,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.03) 1px, transparent 1px)",
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
    padding: 48,
    width: "100%",
    maxWidth: 440,
    position: "relative",
    zIndex: 2,
  },
  glassShine: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: "50%",
    borderRadius: "28px 28px 0 0",
    background: "linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%)",
    pointerEvents: "none",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    marginBottom: 40,
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
    position: "relative",
    overflow: "hidden",
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
    marginBottom: 32,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 22,
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "#7a8490",
    letterSpacing: "0.02em",
  },
  inputWrapper: {
    position: "relative",
  },
  input: {
    width: "100%",
    padding: "13px 16px",
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
    transition: "color 0.2s",
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
    marginTop: 8,
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
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    marginTop: 28,
  },
  link: {
    color: "#7c3aed",
    textDecoration: "none",
    fontSize: 14,
    fontWeight: 500,
    transition: "color 0.2s",
  },
  divider: {
    color: "#7a8490",
    fontSize: 13,
  },
};

/* ───── Animation variants ───── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputId = React.useId();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const user = await login(formData.email, formData.password);
      navigate(user?.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) {
      console.error("[Login] Error:", err);
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map(e => e.msg || e.message || JSON.stringify(e)).join(". "));
      } else if (detail && typeof detail === "object") {
        setError(detail.msg || detail.message || JSON.stringify(detail));
      } else if (err.message === "Network Error") {
        setError("Cannot connect to server. Make sure the backend is running on port 8000.");
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Background effects */}
      <GridOverlay />
      <FloatingOrb size={280} color="#7c3aed" top="-5%" left="-8%" delay={0} />
      <FloatingOrb size={200} color="#3b82f6" top="65%" left="75%" delay={2} />
      <FloatingOrb size={150} color="#ec4899" top="80%" left="10%" delay={4} />

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
            Sign in to your interview assistant
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
            <motion.div style={styles.inputGroup} variants={itemVariants}>
              <label style={styles.label} htmlFor={`email-${inputId}`}>Email Address</label>
              <input
                id={`email-${inputId}`}
                type="email"
                style={styles.input}
                placeholder="Enter your email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                autoComplete="email"
                onFocus={(e) => {
                  e.target.style.borderColor = "rgba(124,58,237,0.5)";
                  e.target.style.boxShadow = "0 0 20px rgba(124,58,237,0.15)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255,255,255,0.07)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </motion.div>

            <motion.div style={styles.inputGroup} variants={itemVariants}>
              <label style={styles.label} htmlFor={`password-${inputId}`}>Password</label>
              <div style={styles.inputWrapper}>
                <input
                  id={`password-${inputId}`}
                  type={showPassword ? "text" : "password"}
                  style={{ ...styles.input, paddingRight: 44 }}
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  autoComplete="current-password"
                  onFocus={(e) => {
                    e.target.style.borderColor = "rgba(124,58,237,0.5)";
                    e.target.style.boxShadow = "0 0 20px rgba(124,58,237,0.15)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255,255,255,0.07)";
                    e.target.style.boxShadow = "none";
                  }}
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
            </motion.div>

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
                  <LogIn size={18} />
                )}
                {loading ? "Signing in..." : "Sign In"}
                {!loading && <Sparkles size={14} style={{ opacity: 0.5 }} />}
              </motion.button>
            </motion.div>
          </form>

          <motion.div style={styles.links} variants={itemVariants}>
            <Link to="/forgot-password" style={styles.link}>
              Forgot Password?
            </Link>
            <span style={styles.divider}>Don't have an account?</span>
            <Link to="/signup" style={styles.link}>
              Create Account
            </Link>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
}
