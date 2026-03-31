import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Terminal, Code, Folder, Eye, EyeOff, Brain, User, ArrowLeft, Cpu, Zap, Shield, Activity, Database } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const QUESTION_DATA = {
  Python: [
    { q: "What is the difference between list and tuple?", tip: "Lists are mutable, Tuples are immutable.", details: "Use lists when you need to modify data. Use tuples for fixed collections.", difficulty: "Easy" },
    { q: "Explain decorators in Python.", tip: "Functions that modify other functions.", details: "They allow you to wrap another function to extend behavior without modifying it.", difficulty: "Medium" },
    { q: "How does memory management work in Python?", tip: "Reference counting & Garbage collection.", details: "Python uses a private heap containing all objects and data structures.", difficulty: "Hard" },
    { q: "What are Python Generators?", tip: "Functions that return an iterator using Yield.", details: "Generators allow you to declare a function that behaves like an iterator.", difficulty: "Medium" },
    { q: "Difference between .py and .pyc files?", tip: ".py is source, .pyc is compiled bytecode.", details: ".pyc files are created by the interpreter when a .py file is imported.", difficulty: "Easy" },
    { q: "What is 'self' in Python?", tip: "Instance of the class.", details: "It's used to access variables that belong to the class.", difficulty: "Easy" },
    { q: "Explain list comprehensions.", tip: "Concise way to create lists.", details: "[expression for item in iterable if condition]", difficulty: "Easy" },
    { q: "What are *args and **kwargs?", tip: "Variable number of arguments.", details: "*args for positional, **kwargs for keyword arguments.", difficulty: "Medium" },
    { q: "Describe the Global Interpreter Lock (GIL).", tip: "Mutex that protects access to Python objects.", details: "Prevents multiple native threads from executing Python bytecodes at once.", difficulty: "Hard" },
    { q: "How do you handle exceptions in Python?", tip: "Try-Except-Finally blocks.", details: "Used to catch and handle errors gracefully.", difficulty: "Easy" },
    { q: "What is the difference between deep and shallow copy?", tip: "Recursive vs one-level copy.", details: "Shallow copy creates a new object but inserts references to original items.", difficulty: "Medium" },
    { q: "What are lambda functions?", tip: "Anonymous single-expression functions.", details: "Defined using the lambda keyword.", difficulty: "Easy" },
    { q: "Explain the 'with' statement.", tip: "Context managers for resource management.", details: "Ensures resources like files are closed properly.", difficulty: "Medium" },
    { q: "What is mocking in Python tests?", tip: "Replacing parts of system with mock objects.", details: "Used to isolate code under test.", difficulty: "Hard" },
    { q: "Difference between range and xrange?", tip: "Python 2 specific (list vs generator).", details: "In Python 3, range is like xrange.", difficulty: "Medium" }
  ],
  Java: [
    { q: "What is the difference between JDK, JRE, and JVM?", tip: "Dev Kit > Runtime > Virtual Machine.", details: "JDK for dev, JRE for running, JVM executes bytecode.", difficulty: "Easy" },
    { q: "Explain the concept of OOPs.", tip: "Object-Oriented Programming System.", details: "Inheritance, Polymorphism, Encapsulation, Abstraction.", difficulty: "Medium" },
    { q: "Difference between equals() and == ?", tip: "Value vs Reference comparison.", details: "equals() compares content, == checks memory location.", difficulty: "Easy" },
    { q: "Why is Java not 100% Object Oriented?", tip: "Primitive data types.", details: "Uses int, char, etc. which are not objects.", difficulty: "Medium" },
    { q: "What is the 'final' keyword?", tip: "Constants and restrictions.", details: "Prevents modification of variables, methods, or classes.", difficulty: "Easy" },
    { q: "Explain the 'static' keyword.", tip: "Belongs to the class, not instances.", details: "Used for memory management mainly.", difficulty: "Medium" },
    { q: "Difference between Interface and Abstract Class?", tip: "Multiple inheritance vs base class.", details: "Interfaces have only abstract methods (mostly).", difficulty: "Medium" },
    { q: "What is exception propagation?", tip: "Exception moving up the call stack.", details: "When not caught, it moves to the calling method.", difficulty: "Hard" },
    { q: "Explain the Diamond Problem in Java.", tip: "Multiple inheritance ambiguity.", details: "Java avoids this by not supporting multiple inheritance for classes.", difficulty: "Hard" },
    { q: "What is the Garbage Collector?", tip: "Automatic memory management.", details: "Deletes unused objects to reclaim memory.", difficulty: "Easy" },
    { q: "Difference between ArrayList and LinkedList?", tip: "Dynamic array vs Doubly linked list.", details: "ArrayList is better for search; LinkedList for insertions.", difficulty: "Medium" },
    { q: "What are Annotations?", tip: "Metadata for code.", details: "Used by compiler or runtime (e.g., @Override).", difficulty: "Easy" },
    { q: "Explain the 'volatile' keyword.", tip: "Visibility across threads.", details: "Ensures value is read from main memory, not cache.", difficulty: "Hard" },
    { q: "What is Reflection in Java?", tip: "Inspect/modify runtime behavior.", details: "Examine classes, fields, methods at runtime.", difficulty: "Hard" },
    { q: "Difference between checked and unchecked exceptions?", tip: "Compile-time vs Runtime.", details: "Checked must be handled; Unchecked occur at runtime.", difficulty: "Medium" }
  ],
  React: [
    { q: "What is the Virtual DOM?", tip: "Lightweight copy of the real DOM.", details: "React updates Virtual DOM first, then syncs changes.", difficulty: "Easy" },
    { q: "Explain React Hooks.", tip: "Use state/lifecycle in functional components.", details: "useState, useEffect, useContext, etc.", difficulty: "Medium" },
    { q: "What is the difference between state and props?", tip: "Internal vs External data.", details: "Props are read-only; State is managed within the component.", difficulty: "Easy" },
    { q: "What is JSX?", tip: "JavaScript XML.", details: "Syntax extension for JS that looks like HTML.", difficulty: "Easy" },
    { q: "Explain the useEffect dependency array.", tip: "Controls when the effect runs.", details: "Empty array = once on mount; No array = every render.", difficulty: "Medium" },
    { q: "What is React Context API?", tip: "Global state management.", details: "Avoids 'prop drilling' through components.", difficulty: "Medium" },
    { q: "Difference between Class and Functional components?", tip: "Legacy vs Modern React.", details: "Functional components use hooks; Class uses lifecycle methods.", difficulty: "Easy" },
    { q: "What are Higher-Order Components (HOC)?", tip: "Functions that take a component and return a new one.", details: "Used for reusing component logic.", difficulty: "Hard" },
    { q: "Explain the 'key' prop in lists.", tip: "Helps React identify which items changed.", details: "Necessary for efficient DOM updates.", difficulty: "Easy" },
    { q: "What is Code Splitting in React?", tip: "Loading code in chunks.", details: "Uses React.lazy and Suspense to improve performance.", difficulty: "Hard" },
    { q: "What is 'lifting state up'?", tip: "Moving state to the nearest common ancestor.", details: "Used for sharing state between sibling components.", difficulty: "Medium" },
    { q: "Explain Redux vs Context API.", tip: "Complex vs Simple state management.", details: "Redux has middle-wares and dev-tools.", difficulty: "Hard" },
    { q: "What is the 'useMemo' hook?", tip: "Memoize expensive calculations.", details: "Only re-calculates when dependencies change.", difficulty: "Hard" },
    { q: "How do you handle forms in React?", tip: "Controlled vs Uncontrolled components.", details: "Controlled uses state to manage input values.", difficulty: "Medium" },
    { q: "What is React Portal?", tip: "Render children outside the parent DOM hierarchy.", details: "Useful for modals and tooltips.", difficulty: "Hard" }
  ],
  NodeJS: [
    { q: "What is Node.js?", tip: "JS runtime built on Chrome's V8 engine.", details: "Uses event-driven, non-blocking I/O model.", difficulty: "Easy" },
    { q: "Explain the Event Loop.", tip: "Heart of Node's concurrency.", details: "Handles callbacks and non-blocking operations.", difficulty: "Hard" },
    { q: "What is npm?", tip: "Node Package Manager.", details: "World's largest software registry for JS packages.", difficulty: "Easy" },
    { q: "Difference between setImmediate and process.nextTick?", tip: "Execution order in event loop.", details: "nextTick runs before any IO; setImmediate runs in the Check phase.", difficulty: "Hard" },
    { q: "What is a Buffer in Node.js?", tip: "Temporarily stored raw data.", details: "Used to handle binary data instead of strings.", difficulty: "Medium" },
    { q: "Explain Stream API.", tip: "Read/write data piece by piece.", details: "Readable, Writable, Duplex, and Transform streams.", difficulty: "Hard" },
    { q: "What is middleware in Express?", tip: "Functions with access to req/res.", details: "Executed during the lifecycle of a request.", difficulty: "Medium" },
    { q: "Difference between fs.readFile and fs.createReadStream?", tip: "Entire file vs chunks.", details: "Streams are memory-efficient for large files.", difficulty: "Medium" },
    { q: "What are worker threads?", tip: "Run JS in parallel threads.", details: "Useful for CPU-intensive tasks without blocking event loop.", difficulty: "Hard" },
    { q: "Explain Clustering in Node.js.", tip: "Utilize all CPU cores.", details: "Creates multiple instances of the same server.", difficulty: "Medium" },
    { q: "What is the purpose of module.exports?", tip: "Export functions/objects from a file.", details: "Used for code modularity.", difficulty: "Easy" },
    { q: "How do you handle errors in async code?", tip: "Try/Catch with await or .catch().", details: "Always handle errors to prevent process crashes.", difficulty: "Easy" },
    { q: "What is REPL in Node.js?", tip: "Read-Eval-Print Loop.", details: "Shell environment for testing Node.js snippets.", difficulty: "Easy" },
    { q: "Explain the package.json file.", tip: "Manifest file for the project.", details: "List dependencies, scripts, and metadata.", difficulty: "Easy" },
    { q: "What is body-parser?", tip: "Parse incoming request bodies.", details: "Express middleware (now mostly built-in).", difficulty: "Easy" }
  ],
  MongoDB: [
    { q: "What is MongoDB?", tip: "NoSQL Document database.", details: "Stores data in JSON-like BSON format.", difficulty: "Easy" },
    { q: "Differences between SQL and NoSQL?", tip: "Relational vs Non-relational.", details: "MongoDB is schema-less and horizontally scalable.", difficulty: "Medium" },
    { q: "What are Collections and Documents?", tip: "Equivalents of Tables and Rows.", details: "Documents are stored within collections.", difficulty: "Easy" },
    { q: "Explain Sharding in MongoDB.", tip: "Horizontal scaling mechanism.", details: "Distributes data across multiple servers.", difficulty: "Hard" },
    { q: "What is the Aggregation Framework?", tip: "Processing data records.", details: "Pipe-based transformations like match, group, sort.", difficulty: "Hard" },
    { q: "What is a replica set?", tip: "Group of MongoDB instances.", details: "Provides high availability and redundancy.", difficulty: "Medium" },
    { q: "Explain Indexes in MongoDB.", tip: "Improve query performance.", details: "Avoids collection scanning by using data structures.", difficulty: "Medium" },
    { q: "What is BSON?", tip: "Binary JSON.", details: "Extended version of JSON with more data types like Date.", difficulty: "Easy" },
    { q: "What are capped collections?", tip: "Fixed-size collections.", details: "Auto-overwrite old data when full; preserves order.", difficulty: "Hard" },
    { q: "Explain the '_id' field.", tip: "Unique identifier for documents.", details: "Usually an ObjectId (12-byte hex).", difficulty: "Easy" },
    { q: "How does MongoDB handle transactions?", tip: "Multi-document ACID transactions.", details: "Available since version 4.0.", difficulty: "Hard" },
    { q: "What is a covered query?", tip: "Query satisfied entirely by an index.", details: "No need to look at actual documents.", difficulty: "Medium" },
    { q: "Explain GridFS.", tip: "Store very large files (>16MB).", details: "Splits file into chunks for storage.", difficulty: "Hard" },
    { q: "What is embedding vs referencing?", tip: "Nested docs vs IDs.", details: "Embed for 'one-to-few'; Reference for 'one-to-many'.", difficulty: "Medium" },
    { q: "What is the 'upsert' option?", tip: "Update or insert.", details: "Creates a new doc if no match is found.", difficulty: "Easy" }
  ],
  HR: [
    { q: "Tell me about yourself.", tip: "Focus on professional journey.", details: "Start with current role, key achievements, then past experience.", difficulty: "Easy" },
    { q: "What are your weaknesses?", tip: "Turn a negative into a positive.", details: "Mention a real weakness and how you are working to improve it.", difficulty: "Medium" },
    { q: "Why should we hire you?", tip: "Match skills to job description.", details: "Highlight your unique fit for the role.", difficulty: "Hard" },
    { q: "Where do you see yourself in 5 years?", tip: "Align with company goals.", details: "Show ambition and interest in growing within the company.", difficulty: "Medium" },
    { q: "How do you handle conflict?", tip: "STAR method.", details: "Situation, Task, Action, Result. Focus on resolution.", difficulty: "Hard" },
    { q: "What are your salary expectations?", tip: "Research market rates.", details: "Be flexible but have a range in mind.", difficulty: "Medium" },
    { q: "Why do you want to leave your current job?", tip: "Stay positive about the future.", details: "Focus on seeking growth or new challenges.", difficulty: "Medium" },
    { q: "Explain a time you failed.", tip: "Show learning and resilience.", details: "Analyze what went wrong and how you improved.", difficulty: "Hard" },
    { q: "Describe your leadership style.", tip: "Servant leadership or collaborative.", details: "Give examples of leading a team.", difficulty: "Medium" },
    { q: "What motivates you?", tip: "Personal and professional drivers.", details: "Solving problems, learning, team success.", difficulty: "Easy" },
    { q: "How do you handle pressure?", tip: "Prioritization and organization.", details: "Discuss staying calm and focused.", difficulty: "Medium" },
    { q: "Do you have any questions for us?", tip: "Show genuine interest.", details: "Ask about team culture, company vision, etc.", difficulty: "Easy" },
    { q: "What is your biggest achievement?", tip: "Quantifiable results.", details: "Highlight a project that had a major impact.", difficulty: "Medium" },
    { q: "How do you handle feedback?", tip: "Openness and growth mindset.", details: "View feedback as an opportunity to learn.", difficulty: "Easy" },
    { q: "Describe a difficult team member situation.", tip: "Professionalism and empathy.", details: "How did you work through differences?", difficulty: "Hard" }
  ],
  OS: [
    { q: "What is an Operating System?", tip: "Interface between hardware and users.", details: "Manages resources and provides common services.", difficulty: "Easy" },
    { q: "Explain Process vs Thread.", tip: "Execution contexts.", details: "Process has its own memory; threads share memory.", difficulty: "Medium" },
    { q: "What is Virtual Memory?", tip: "Abstracting physical memory.", details: "Allows execution of processes larger than physical RAM.", difficulty: "Hard" },
    { q: "Explain Paging vs Segmentation.", tip: "Memory management schemes.", details: "Paging is fixed size; Segmentation is logical units.", difficulty: "Medium" },
    { q: "What is a Deadlock?", tip: "Circular dependency on resources.", details: "Mutual exclusion, Hold and wait, No preemption, Circular wait.", difficulty: "Hard" },
    { q: "What is a Kernel?", tip: "Core part of the OS.", details: "Manages memory, task scheduling, and hardware drivers.", difficulty: "Easy" },
    { q: "Explain Context Switching.", tip: "Saving/loading CPU state.", details: "Switching from one process to another.", difficulty: "Medium" },
    { q: "What are Semaphores?", tip: "Synchronization primitives.", details: "Used to manage concurrent access to resources.", difficulty: "Hard" },
    { q: "Difference between Monolithic and Microkernel?", tip: "OS architecture.", details: "Monolithic is one large process; Microkernel is modular.", difficulty: "Medium" },
    { q: "What is Thrashing?", tip: "High page fault rate.", details: "System spends more time swapping than executing.", difficulty: "Hard" },
    { q: "Explain the Banker's Algorithm.", tip: "Deadlock avoidance.", details: "Allocates resources safely based on maximum claims.", difficulty: "Hard" },
    { q: "What is GUI vs CLI?", tip: "Visual vs Text interface.", details: "Graphical User Interface vs Command Line Interface.", difficulty: "Easy" },
    { q: "What is Dual Mode operation?", tip: "User mode vs Kernel mode.", details: "Protects hardware from rogue user programs.", difficulty: "Medium" },
    { q: "Explain RAID.", tip: "Redundant Array of Independent Disks.", details: "Used for data redundancy and performance.", difficulty: "Medium" },
    { q: "What is a Shell?", tip: "Command interpreter.", details: "Layer between user and kernel (e.g., bash, zsh).", difficulty: "Easy" }
  ],
  Networks: [
    { q: "What is the OSI Model?", tip: "7 layers of networking.", details: "Physical, Data Link, Network, Transport, Session, Presentation, Application.", difficulty: "Easy" },
    { q: "Difference between TCP and UDP?", tip: "Connection-oriented vs Connectionless.", details: "TCP is reliable and slow; UDP is fast and unreliable.", difficulty: "Medium" },
    { q: "What is an IP Address?", tip: "Unique identifier for devices.", details: "IPv4 (32-bit) and IPv6 (128-bit).", difficulty: "Easy" },
    { q: "Explain DNS.", tip: "Domain Name System.", details: "Translates human URLs to numerical IP addresses.", difficulty: "Easy" },
    { q: "What is HTTP vs HTTPS?", tip: "Hypertext Transfer Protocol (Secure).", details: "HTTPS uses SSL/TLS for encryption.", difficulty: "Easy" },
    { q: "Explain 3-way Handshake.", tip: "TCP connection setup.", details: "SYN -> SYN-ACK -> ACK.", difficulty: "Medium" },
    { q: "What is a Firewall?", tip: "Network security system.", details: "Filters incoming/outgoing traffic based on rules.", difficulty: "Easy" },
    { q: "Difference between Hub, Switch, and Router?", tip: "Broadcast vs Targeted vs Inter-network.", details: "Router works at Layer 3; Switch at Layer 2.", difficulty: "Medium" },
    { q: "What is a VPN?", tip: "Virtual Private Network.", details: "Secure tunnel over a public network.", difficulty: "Easy" },
    { q: "Explain DHCP.", tip: "Dynamic Host Configuration Protocol.", details: "Assigns IP addresses automatically.", difficulty: "Easy" },
    { q: "What is Latency and Bandwidth?", tip: "Delay vs Capacity.", details: "Latency is time to travel; Bandwidth is amount per second.", difficulty: "Medium" },
    { q: "What is a Default Gateway?", tip: "Exit point for local traffic.", details: "IP of the router on the local network.", difficulty: "Easy" },
    { q: "Explain ARP.", tip: "Address Resolution Protocol.", details: "Resolves IP addresses to MAC addresses.", difficulty: "Medium" },
    { q: "What is an ISP?", tip: "Internet Service Provider.", details: "Company that provides internet access.", difficulty: "Easy" },
    { q: "What is BGP?", tip: "Border Gateway Protocol.", details: "Routing protocol for the entire Internet.", difficulty: "Hard" }
  ],
  SQL: [
    { q: "What is SQL?", tip: "Structured Query Language.", details: "Standard language for managing relational databases.", difficulty: "Easy" },
    { q: "Difference between Inner and Outer join?", tip: "Intersection vs Union (sort of).", details: "Inner Join returns only matching rows.", difficulty: "Medium" },
    { q: "What is a Primary Key?", tip: "Unique identifier for rows.", details: "Must be unique and not null.", difficulty: "Easy" },
    { q: "Explain Indexes in SQL.", tip: "Speed up data retrieval.", details: "Uses B-trees to avoid full table scans.", difficulty: "Medium" },
    { q: "What are ACID properties?", tip: "Atomicity, Consistency, Isolation, Durability.", details: "Ensures database reliability.", difficulty: "Hard" },
    { q: "Difference between DELETE and TRUNCATE?", tip: "DML vs DDL.", details: "Truncate is faster and doesn't log individual row deletions.", difficulty: "Medium" },
    { q: "What is a Foreign Key?", tip: "Links two tables together.", details: "A field in one table that refers to Primary Key of another.", difficulty: "Easy" },
    { q: "Explain Normalization.", tip: "Reducing data redundancy.", details: "1NF, 2NF, 3NF, BCNF.", difficulty: "Hard" },
    { q: "What is the GROUP BY clause?", tip: "Aggregate data by columns.", details: "Used with SUM, COUNT, AVG, etc.", difficulty: "Medium" },
    { q: "Explain Transactions in SQL.", tip: "Sequence of operations treated as a unit.", details: "Uses COMMIT and ROLLBACK.", difficulty: "Medium" },
    { q: "What is a View?", tip: "Virtual table based on a query.", details: "Stores the query, not the data.", difficulty: "Medium" },
    { q: "Difference between WHERE and HAVING?", tip: "Row filter vs Group filter.", details: "HAVING is used with Aggregate functions.", difficulty: "Medium" },
    { q: "What is a Stored Procedure?", tip: "Pre-compiled SQL code.", details: "Saved in the database for reuse.", difficulty: "Hard" },
    { q: "What is an Alias in SQL?", tip: "Temporary name for table/column.", details: "Uses the AS keyword.", difficulty: "Easy" },
    { q: "Explain DB Triggers.", tip: "Auto-executed SQL on specific events.", details: "Runs before/after Insert, Update, or Delete.", difficulty: "Hard" }
  ]
};

const TAB_ICONS = { 
  Python: Terminal, 
  Java: Code, 
  React: Cpu, 
  NodeJS: Zap, 
  MongoDB: Database, 
  HR: Folder, 
  OS: Shield, 
  Networks: Activity, 
  SQL: Brain 
};

const TAB_COLORS = { 
  Python: "#3b82f6", 
  Java: "#f59e0b", 
  React: "#06b6d4", 
  NodeJS: "#22c55e", 
  MongoDB: "#10b981", 
  HR: "#ec4899", 
  OS: "#ef4444", 
  Networks: "#6366f1", 
  SQL: "#7c3aed" 
};

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
    maxWidth: 900,
    margin: "0 auto",
    padding: "40px 32px",
    position: "relative",
    zIndex: 1,
  },
  header: {
    textAlign: "center",
    marginBottom: 36,
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
    maxWidth: 500,
    margin: "0 auto",
    lineHeight: 1.5,
  },
  tabRow: {
    display: "flex",
    justifyContent: "center",
    gap: 12,
    marginBottom: 32,
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 22px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    color: "#9aa6b2",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.3s",
    backdropFilter: "blur(10px)",
  },
  tabActive: {
    background: "rgba(124,58,237,0.15)",
    borderColor: "rgba(124,58,237,0.4)",
    color: "#fff",
    boxShadow: "0 0 20px rgba(124,58,237,0.15)",
  },
  card: {
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 16,
    overflow: "hidden",
    marginBottom: 14,
    boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)",
    transition: "border-color 0.3s",
  },
  cardContent: {
    padding: 24,
  },
  difficultyBadge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 20,
    fontSize: 10,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 8,
  },
  questionText: {
    fontSize: 17,
    fontWeight: 600,
    color: "#fff",
    lineHeight: 1.4,
  },
  revealBtn: {
    background: "none",
    border: "none",
    color: "#7a8490",
    cursor: "pointer",
    padding: 6,
    borderRadius: 8,
    transition: "color 0.2s",
  },
  tipArea: {
    borderTop: "1px solid rgba(255,255,255,0.05)",
    marginTop: 16,
    paddingTop: 16,
  },
  tipLabel: {
    fontSize: 12,
    fontWeight: 700,
    color: "#a78bfa",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    marginBottom: 6,
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  tipText: {
    fontSize: 14,
    color: "#e6eef8",
    marginBottom: 8,
  },
  detailBox: {
    padding: 12,
    borderRadius: 10,
    background: "rgba(124,58,237,0.06)",
    border: "1px solid rgba(124,58,237,0.12)",
    fontSize: 13,
    color: "#9aa6b2",
    fontStyle: "italic",
    lineHeight: 1.5,
  },
};

function getDifficultyStyle(diff) {
  if (diff === "Easy") return { background: "rgba(34,197,94,0.12)", color: "#4ade80" };
  if (diff === "Medium") return { background: "rgba(245,158,11,0.12)", color: "#fbbf24" };
  return { background: "rgba(239,68,68,0.12)", color: "#f87171" };
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
};

export default function QuestionBank() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("Python");
  const [revealedIds, setRevealedIds] = useState({});

  const toggleReveal = (idx) => {
    setRevealedIds((prev) => ({
      ...prev,
      [`${activeTab}-${idx}`]: !prev[`${activeTab}-${idx}`],
    }));
  };

  return (
    <div style={styles.container}>
      <FloatingOrb size={350} color="#7c3aed" top="-8%" left="-5%" delay={0} />
      <FloatingOrb size={250} color="#3b82f6" top="55%" left="82%" delay={2} />
      <FloatingOrb size={180} color="#ec4899" top="75%" left="10%" delay={4} />

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
        <span style={{ fontSize: 16, fontWeight: 600, color: "#fff" }}>Question Bank</span>
        <div style={{ width: 150 }} />
      </nav>

      <main style={styles.main}>
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          {/* Header */}
          <motion.div style={styles.header} variants={itemVariants}>
            <h1 style={styles.title}>Interview Question Bank</h1>
            <p style={styles.subtitle}>
              Prepare with curated questions across technical and behavioral domains
            </p>
          </motion.div>

          {/* Tabs */}
          <motion.div style={styles.tabRow} variants={itemVariants}>
            {Object.keys(QUESTION_DATA).map((tab) => {
              const Icon = TAB_ICONS[tab];
              const isActive = activeTab === tab;
              return (
                <motion.button
                  key={tab}
                  style={{
                    ...styles.tab,
                    ...(isActive ? styles.tabActive : {}),
                  }}
                  onClick={() => setActiveTab(tab)}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                >
                  <Icon size={16} />
                  {tab}
                </motion.button>
              );
            })}
          </motion.div>

          {/* Questions */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25 }}
            >
              {QUESTION_DATA[activeTab].map((item, idx) => {
                const isRevealed = revealedIds[`${activeTab}-${idx}`];
                const diffStyle = getDifficultyStyle(item.difficulty);

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.08 }}
                    style={{
                      ...styles.card,
                      borderColor: isRevealed ? "rgba(124,58,237,0.3)" : "rgba(255,255,255,0.07)",
                    }}
                  >
                    <div style={styles.cardContent}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <div style={{ flex: 1 }}>
                          <span style={{ ...styles.difficultyBadge, ...diffStyle }}>
                            {item.difficulty}
                          </span>
                          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                            <div style={{
                              width: 30, height: 30, borderRadius: 8,
                              background: "rgba(124,58,237,0.12)", color: "#a78bfa",
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: 13, fontWeight: 700, flexShrink: 0, marginTop: 2,
                            }}>
                              {idx + 1}
                            </div>
                            <h3 style={styles.questionText}>{item.q}</h3>
                          </div>
                        </div>
                        <motion.button
                          style={styles.revealBtn}
                          onClick={() => toggleReveal(idx)}
                          whileHover={{ color: "#a78bfa" }}
                          title={isRevealed ? "Hide answer" : "Show answer"}
                        >
                          {isRevealed ? <EyeOff size={18} /> : <Eye size={18} />}
                        </motion.button>
                      </div>

                      <AnimatePresence>
                        {isRevealed && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            style={{ overflow: "hidden" }}
                          >
                            <div style={styles.tipArea}>
                              <div style={styles.tipLabel}>
                                <Brain size={14} />
                                Quick Tip
                              </div>
                              <p style={styles.tipText}>{item.tip}</p>
                              <div style={styles.detailBox}>
                                "{item.details}"
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </main>
    </div>
  );
}
