import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import { motion } from "framer-motion";
import {
  Users,
  FileVideo,
  TrendingUp,
  LogOut,
  RefreshCw,
  Shield,
  UserCheck,
  BarChart3,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

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
    width: 40,
    height: 40,
    borderRadius: 10,
    background: "linear-gradient(135deg, #ef4444, #dc2626)",
    boxShadow: "0 0 15px rgba(239,68,68,0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
  },
  logoText: {
    display: "flex",
    flexDirection: "column",
  },
  logoTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: "#fff",
  },
  logoSubtitle: {
    fontSize: 12,
    color: "#ef4444",
    fontWeight: 500,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 12,
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
    fontSize: 13,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  refreshBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    color: "#9aa6b2",
    fontSize: 13,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  logoutBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid rgba(239,68,68,0.2)",
    background: "rgba(239,68,68,0.06)",
    color: "#f87171",
    fontSize: 13,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  main: {
    maxWidth: 1400,
    margin: "0 auto",
    padding: "32px",
    position: "relative",
    zIndex: 1,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 8,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 14,
    color: "#7a8490",
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 16,
    marginBottom: 32,
  },
  metricCard: {
    padding: 24,
    borderRadius: 16,
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
    transition: "border-color 0.3s",
  },
  metricHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  metricIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  metricLabel: {
    fontSize: 13,
    color: "#7a8490",
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 32,
    fontWeight: 700,
    color: "#fff",
  },
  metricChange: {
    fontSize: 12,
    marginTop: 8,
    color: "#7a8490",
  },
  chartsRow: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr",
    gap: 16,
    marginBottom: 32,
  },
  chartCard: {
    padding: 24,
    borderRadius: 16,
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "#fff",
    marginBottom: 20,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  tableCard: {
    padding: 24,
    borderRadius: 16,
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
  },
  tableTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "#fff",
    marginBottom: 20,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  th: {
    textAlign: "left",
    padding: "12px 16px",
    fontSize: 12,
    fontWeight: 600,
    color: "#7a8490",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  td: {
    padding: "14px 16px",
    fontSize: 14,
    color: "#e6eef8",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  userCell: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 10,
    background: "linear-gradient(135deg, #7c3aed, #5b21b6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
  },
  roleBadge: {
    padding: "4px 12px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 500,
  },
  adminBadge: {
    background: "rgba(239,68,68,0.1)",
    color: "#f87171",
  },
  userBadge: {
    background: "rgba(34,197,94,0.1)",
    color: "#4ade80",
  },
  loading: {
    textAlign: "center",
    padding: 80,
  },
  error: {
    textAlign: "center",
    padding: 60,
  },
};

const COLORS = ["#7c3aed", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6"];

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

export default function Admin() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError("");

    try {
      const [statsRes, usersRes] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/users?limit=10"),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <FloatingOrb size={350} color="#ef4444" top="-5%" left="-3%" delay={0} />
        <FloatingOrb size={250} color="#7c3aed" top="60%" left="80%" delay={2} />
        <nav style={styles.navbar}>
          <div style={styles.logo}>
            <div style={styles.logoIcon}><Shield size={20} /></div>
            <div style={styles.logoText}>
              <span style={styles.logoTitle}>Smart AI</span>
              <span style={styles.logoSubtitle}>Admin Panel</span>
            </div>
          </div>
        </nav>
        <div style={styles.loading}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            style={{ display: "inline-block" }}
          >
            <Loader2 size={32} color="#7c3aed" />
          </motion.div>
          <p style={{ color: "#7a8490", marginTop: 16 }}>Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <FloatingOrb size={350} color="#ef4444" top="-5%" left="-3%" delay={0} />
        <nav style={styles.navbar}>
          <div style={styles.logo}>
            <div style={styles.logoIcon}><Shield size={20} /></div>
            <div style={styles.logoText}>
              <span style={styles.logoTitle}>Smart AI</span>
              <span style={styles.logoSubtitle}>Admin Panel</span>
            </div>
          </div>
          <div style={styles.headerRight}>
            <motion.button
              style={styles.backBtn}
              onClick={() => navigate("/dashboard")}
              whileHover={{ scale: 1.03, borderColor: "rgba(124,58,237,0.3)", color: "#fff" }}
              whileTap={{ scale: 0.97 }}
            >
              <ArrowLeft size={15} />
              Dashboard
            </motion.button>
            <motion.button style={styles.refreshBtn} onClick={fetchData} whileHover={{ scale: 1.03 }}>
              <RefreshCw size={15} />
              Retry
            </motion.button>
          </div>
        </nav>
        <div style={styles.error}>
          <div style={{
            display: "inline-block", padding: "40px 60px", borderRadius: 20,
            background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)",
          }}>
            <p style={{ color: "#f87171", fontSize: 16, marginBottom: 8 }}>{error}</p>
            <p style={{ color: "#7a8490", fontSize: 14 }}>Try refreshing or check the backend connection.</p>
          </div>
        </div>
      </div>
    );
  }

  const difficultyData = Object.entries(stats?.sessions_by_difficulty || {}).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value,
  }));

  const roleData = Object.entries(stats?.users_by_role || {}).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value,
  }));

  return (
    <div style={styles.container}>
      <FloatingOrb size={400} color="#ef4444" top="-8%" left="-5%" delay={0} />
      <FloatingOrb size={300} color="#7c3aed" top="50%" left="80%" delay={2} />
      <FloatingOrb size={200} color="#3b82f6" top="80%" left="15%" delay={4} />

      {/* Navbar */}
      <motion.nav
        style={styles.navbar}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div style={styles.logo}>
          <div style={styles.logoIcon}>
            <Shield size={20} />
          </div>
          <div style={styles.logoText}>
            <span style={styles.logoTitle}>Smart AI</span>
            <span style={styles.logoSubtitle}>Admin Panel</span>
          </div>
        </div>

        <div style={styles.headerRight}>
          <motion.button
            style={styles.backBtn}
            onClick={() => navigate("/dashboard")}
            whileHover={{ scale: 1.03, borderColor: "rgba(124,58,237,0.3)", color: "#fff" }}
            whileTap={{ scale: 0.97 }}
          >
            <ArrowLeft size={15} />
            Dashboard
          </motion.button>
          <motion.button style={styles.refreshBtn} onClick={fetchData} whileHover={{ scale: 1.03 }}>
            <RefreshCw size={15} />
            Refresh
          </motion.button>
          <motion.button style={styles.logoutBtn} onClick={handleLogout} whileHover={{ scale: 1.03 }}>
            <LogOut size={15} />
            Sign Out
          </motion.button>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main style={styles.main}>
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <motion.header style={styles.header} variants={itemVariants}>
            <h1 style={styles.title}>Admin Dashboard</h1>
            <p style={styles.subtitle}>
              Welcome back, {user?.username}. Here's an overview of your platform.
            </p>
          </motion.header>

          {/* Metric Cards */}
          <motion.div style={styles.metricsGrid} variants={itemVariants}>
            {[
              { label: "Total Users", value: stats?.total_users || 0, sub: `+${stats?.recent_signups || 0} this week`, subColor: "#22c55e", icon: Users, iconColor: "#7c3aed", iconBg: "rgba(124,58,237,0.1)" },
              { label: "Total Sessions", value: stats?.total_sessions || 0, sub: `${stats?.completed_sessions || 0} completed`, subColor: "#7a8490", icon: FileVideo, iconColor: "#3b82f6", iconBg: "rgba(59,130,246,0.1)" },
              { label: "Average Score", value: stats?.average_score?.toFixed(1) || "0.0", sub: "Out of 100", subColor: "#7a8490", icon: TrendingUp, iconColor: "#22c55e", iconBg: "rgba(34,197,94,0.1)" },
              { label: "Completion Rate", value: `${stats?.total_sessions ? Math.round((stats.completed_sessions / stats.total_sessions) * 100) : 0}%`, sub: "Session completion", subColor: "#7a8490", icon: UserCheck, iconColor: "#f59e0b", iconBg: "rgba(245,158,11,0.1)" },
            ].map((m, i) => (
              <motion.div
                key={i}
                style={styles.metricCard}
                whileHover={{ borderColor: "rgba(124,58,237,0.3)", scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <div style={styles.metricHeader}>
                  <div>
                    <div style={styles.metricLabel}>{m.label}</div>
                    <div style={styles.metricValue}>{m.value}</div>
                  </div>
                  <div style={{ ...styles.metricIcon, background: m.iconBg }}>
                    <m.icon size={22} color={m.iconColor} />
                  </div>
                </div>
                <div style={{ ...styles.metricChange, color: m.subColor }}>{m.sub}</div>
              </motion.div>
            ))}
          </motion.div>

          {/* Charts Row */}
          <motion.div style={styles.chartsRow} variants={itemVariants}>
            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>
                <BarChart3 size={18} color="#7c3aed" />
                Sessions by Difficulty
              </h3>
              {difficultyData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={difficultyData}>
                    <XAxis dataKey="name" tick={{ fill: "#7a8490", fontSize: 12 }} axisLine={false} />
                    <YAxis tick={{ fill: "#7a8490", fontSize: 12 }} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,10,15,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 10,
                        backdropFilter: "blur(10px)",
                      }}
                    />
                    <Bar dataKey="value" fill="#7c3aed" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: "center", padding: 40, color: "#7a8490" }}>
                  No session data yet
                </div>
              )}
            </div>

            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>
                <Users size={18} color="#7c3aed" />
                Users by Role
              </h3>
              {roleData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={roleData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {roleData.map((entry, index) => (
                        <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,10,15,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 10,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: "center", padding: 40, color: "#7a8490" }}>
                  No user data yet
                </div>
              )}
            </div>
          </motion.div>

          {/* Users Table */}
          <motion.div style={styles.tableCard} variants={itemVariants}>
            <h3 style={styles.tableTitle}>
              <Users size={18} color="#7c3aed" />
              Recent Users
            </h3>
            {users.length > 0 ? (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>User</th>
                    <th style={styles.th}>Email</th>
                    <th style={styles.th}>Role</th>
                    <th style={styles.th}>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={styles.td}>
                        <div style={styles.userCell}>
                          <div style={styles.avatar}>
                            {u.username.charAt(0).toUpperCase()}
                          </div>
                          <span>{u.username}</span>
                        </div>
                      </td>
                      <td style={styles.td}>{u.email}</td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.roleBadge,
                            ...(u.role === "admin" ? styles.adminBadge : styles.userBadge),
                          }}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td style={styles.td}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ textAlign: "center", padding: 40, color: "#7a8490" }}>
                No users found
              </div>
            )}
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
}
