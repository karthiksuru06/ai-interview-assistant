/**
 * Browser-Side Face Analyzer
 * ===========================
 * Zero-latency face analysis using MediaPipe Face Landmarker.
 * Runs entirely in the browser — video never leaves the device.
 *
 * Provides:
 *  - Head pose (yaw, pitch, roll)
 *  - Iris gaze tracking (left/right/center/distracted)
 *  - Posture classification (Good/Slouching/Looking Away)
 *  - Basic emotion heuristics from facial geometry
 */

import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

// ── Landmark indices ────────────────────────────────────────────
// MediaPipe Face Mesh 478 landmarks
const NOSE_TIP = 1;
const CHIN = 152;
const LEFT_EYE_OUTER = 33;
const RIGHT_EYE_OUTER = 263;
const LEFT_MOUTH = 61;
const RIGHT_MOUTH = 291;
const UPPER_LIP = 13;
const LOWER_LIP = 14;
const LEFT_EYEBROW_INNER = 107;
const RIGHT_EYEBROW_INNER = 336;
const LEFT_EYEBROW_OUTER = 70;
const RIGHT_EYEBROW_OUTER = 300;
const LEFT_EYE_TOP = 159;
const LEFT_EYE_BOTTOM = 145;
const RIGHT_EYE_TOP = 386;
const RIGHT_EYE_BOTTOM = 374;

// Iris landmarks (enabled with outputFaceBlendshapes or refineLandmarks)
const LEFT_IRIS_CENTER = 468;
const RIGHT_IRIS_CENTER = 473;
const LEFT_EYE_INNER = 133;
const RIGHT_EYE_INNER = 362;

// ── Thresholds ──────────────────────────────────────────────────
const PITCH_SLOUCH_DEG = 20;
const YAW_AWAY_DEG = 30;
const GAZE_DEVIATION_THRESHOLD = 0.22;
const DISTRACTION_MS = 5000;
const NO_FACE_GRACE_MS = 300;

// ── 3D Model Points for solvePnP (in mm, standard face model) ──
const MODEL_POINTS_3D = [
  [0.0, 0.0, 0.0],        // Nose tip
  [0.0, -330.0, -65.0],   // Chin
  [-225.0, 170.0, -135.0], // Left eye outer
  [225.0, 170.0, -135.0],  // Right eye outer
  [-150.0, -150.0, -125.0], // Left mouth
  [150.0, -150.0, -125.0],  // Right mouth
];
const POSE_LANDMARK_IDS = [NOSE_TIP, CHIN, LEFT_EYE_OUTER, RIGHT_EYE_OUTER, LEFT_MOUTH, RIGHT_MOUTH];

class FaceAnalyzer {
  constructor() {
    this.landmarker = null;
    this.ready = false;
    this.loading = false;
    this._gazeOffStart = null;
    this._noFaceStart = null;
    this._lastGoodResult = null;
  }

  async initialize() {
    if (this.ready || this.loading) return;
    this.loading = true;

    try {
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
      );

      this.landmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: "/models/face_landmarker.task",
          delegate: "GPU",
        },
        runningMode: "VIDEO",
        numFaces: 2,
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
      });

      this.ready = true;
      console.log("[FaceAnalyzer] MediaPipe Face Landmarker ready (browser-side)");
    } catch (err) {
      console.error("[FaceAnalyzer] Failed to initialize:", err);
      // Fallback: try CPU delegate
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );
        this.landmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
            delegate: "CPU",
          },
          runningMode: "VIDEO",
          numFaces: 2,
          outputFaceBlendshapes: true,
          outputFacialTransformationMatrixes: true,
        });
        this.ready = true;
        console.log("[FaceAnalyzer] Initialized with CPU fallback");
      } catch (err2) {
        console.error("[FaceAnalyzer] CPU fallback also failed:", err2);
      }
    } finally {
      this.loading = false;
    }
  }

  /**
   * Analyze a video frame. Call this from requestAnimationFrame.
   *
   * @param {HTMLVideoElement} video - The video element to analyze
   * @param {number} timestampMs - Performance.now() timestamp
   * @returns {object} Analysis result
   */
  analyze(video, timestampMs) {
    if (!this.ready || !this.landmarker) {
      return this._default();
    }

    if (video.readyState < 2) {
      return this._default();
    }

    let result;
    try {
      result = this.landmarker.detectForVideo(video, timestampMs);
    } catch (err) {
      // MediaPipe can throw on invalid frames
      return this._lastGoodResult || this._default();
    }

    if (!result.faceLandmarks || result.faceLandmarks.length === 0) {
      return this._handleNoFace();
    }

    if (result.faceLandmarks.length > 1) {
      return { ...this._default(), multipleFaces: true, hasFace: true };
    }

    // Face detected — reset grace timer
    this._noFaceStart = null;

    const landmarks = result.faceLandmarks[0];
    const w = video.videoWidth;
    const h = video.videoHeight;

    // ── Head Pose ──
    const headPose = this._computeHeadPose(landmarks, w, h, result);
    const posture = this._classifyPosture(headPose);

    // ── Gaze ──
    const gazeRatio = this._computeGazeRatio(landmarks, w);
    const eyeContact = this._classifyGaze(gazeRatio);

    // ── Emotion (from blendshapes if available, else from geometry) ──
    const emotion = this._detectEmotion(result.faceBlendshapes, landmarks);

    const analysis = {
      posture,
      eyeContact,
      headPose,
      gazeRatio: Math.round(gazeRatio * 1000) / 1000,
      emotion: emotion.label,
      confidence: emotion.confidence,
      allEmotions: emotion.all,
      hasFace: true,
    };

    this._lastGoodResult = analysis;
    return analysis;
  }

  // ── Head Pose from Transformation Matrix ──────────────────────
  _computeHeadPose(landmarks, w, h, result) {
    // Prefer the transformation matrix from MediaPipe (more accurate)
    if (
      result.facialTransformationMatrixes &&
      result.facialTransformationMatrixes.length > 0
    ) {
      const matrix = result.facialTransformationMatrixes[0].data;
      // Extract rotation from 4x4 column-major matrix
      // matrix layout: [m00, m10, m20, m30, m01, m11, m21, m31, m02, m12, m22, m32, ...]
      const m00 = matrix[0], m10 = matrix[1], m20 = matrix[2];
      const m01 = matrix[4], m11 = matrix[5], m21 = matrix[6];
      const m02 = matrix[8], m12 = matrix[9], m22 = matrix[10];

      const sy = Math.sqrt(m00 * m00 + m10 * m10);
      let pitch, yaw, roll;
      if (sy > 1e-6) {
        pitch = Math.atan2(m21, m22) * (180 / Math.PI);
        yaw = Math.atan2(-m20, sy) * (180 / Math.PI);
        roll = Math.atan2(m10, m00) * (180 / Math.PI);
      } else {
        pitch = Math.atan2(-m12, m11) * (180 / Math.PI);
        yaw = Math.atan2(-m20, sy) * (180 / Math.PI);
        roll = 0;
      }

      return {
        yaw: Math.round(yaw * 10) / 10,
        pitch: Math.round(pitch * 10) / 10,
        roll: Math.round(roll * 10) / 10,
      };
    }

    // Fallback: estimate from landmark positions
    const nose = landmarks[NOSE_TIP];
    const leftEye = landmarks[LEFT_EYE_OUTER];
    const rightEye = landmarks[RIGHT_EYE_OUTER];

    const eyeMidX = (leftEye.x + rightEye.x) / 2;
    const eyeMidY = (leftEye.y + rightEye.y) / 2;

    const yaw = (nose.x - eyeMidX) * 180;
    const pitch = (nose.y - eyeMidY) * 180;
    const roll =
      Math.atan2(rightEye.y - leftEye.y, rightEye.x - leftEye.x) *
      (180 / Math.PI);

    return {
      yaw: Math.round(yaw * 10) / 10,
      pitch: Math.round(pitch * 10) / 10,
      roll: Math.round(roll * 10) / 10,
    };
  }

  _classifyPosture(pose) {
    if (pose.pitch > PITCH_SLOUCH_DEG) return "Slouching";
    if (Math.abs(pose.yaw) > YAW_AWAY_DEG) return "Looking Away";
    return "Good";
  }

  // ── Iris Gaze ─────────────────────────────────────────────────
  _computeGazeRatio(landmarks, w) {
    const _eyeRatio = (irisIdx, innerIdx, outerIdx) => {
      const ix = landmarks[irisIdx].x * w;
      const innerX = landmarks[innerIdx].x * w;
      const outerX = landmarks[outerIdx].x * w;
      const width = Math.abs(innerX - outerX);
      if (width < 1) return 0.5;
      return (ix - Math.min(innerX, outerX)) / width;
    };

    // Check if iris landmarks exist (indices 468-477)
    if (landmarks.length <= LEFT_IRIS_CENTER) {
      return 0.5; // No iris data
    }

    const left = _eyeRatio(LEFT_IRIS_CENTER, LEFT_EYE_INNER, LEFT_EYE_OUTER);
    const right = _eyeRatio(RIGHT_IRIS_CENTER, RIGHT_EYE_INNER, RIGHT_EYE_OUTER);
    return (left + right) / 2;
  }

  _classifyGaze(ratio) {
    const deviation = Math.abs(ratio - 0.5);
    const now = performance.now();

    if (deviation > GAZE_DEVIATION_THRESHOLD) {
      if (this._gazeOffStart === null) this._gazeOffStart = now;
      if (now - this._gazeOffStart >= DISTRACTION_MS) return "Distracted";
      return ratio < 0.3 ? "Left" : ratio > 0.7 ? "Right" : "Center";
    }

    this._gazeOffStart = null;
    return "Center";
  }

  // ── Emotion Detection ─────────────────────────────────────────
  _detectEmotion(blendshapes, landmarks) {
    // Prefer blendshapes (much more accurate)
    if (blendshapes && blendshapes.length > 0) {
      return this._emotionFromBlendshapes(blendshapes[0].categories);
    }
    // Fallback: geometric heuristics
    return this._emotionFromGeometry(landmarks);
  }

  _emotionFromBlendshapes(categories) {
    // MediaPipe blendshapes → emotion mapping
    const bs = {};
    for (const cat of categories) {
      bs[cat.categoryName] = cat.score;
    }

    // Compute emotion probabilities from blendshapes
    const smile = (bs["mouthSmileLeft"] || 0) + (bs["mouthSmileRight"] || 0);
    const frown = (bs["mouthFrownLeft"] || 0) + (bs["mouthFrownRight"] || 0);
    const browDown = (bs["browDownLeft"] || 0) + (bs["browDownRight"] || 0);
    const browUp = (bs["browInnerUp"] || 0);
    const jawOpen = bs["jawOpen"] || 0;
    const eyeWide = (bs["eyeWideLeft"] || 0) + (bs["eyeWideRight"] || 0);
    const eyeSquint = (bs["eyeSquintLeft"] || 0) + (bs["eyeSquintRight"] || 0);
    const mouthOpen = (bs["mouthOpen"] || 0);

    const emotions = {
      happiness: Math.min(1, smile * 0.8 + eyeSquint * 0.2),
      surprise: Math.min(1, (browUp * 0.4 + jawOpen * 0.3 + eyeWide * 0.3)),
      sadness: Math.min(1, frown * 0.6 + browUp * 0.2 + (1 - smile) * 0.2),
      anger: Math.min(1, browDown * 0.5 + frown * 0.3 + eyeSquint * 0.2),
      fear: Math.min(1, eyeWide * 0.4 + browUp * 0.3 + mouthOpen * 0.3),
      disgust: Math.min(1, (bs["noseSneerLeft"] || 0 + bs["noseSneerRight"] || 0) * 0.5 + frown * 0.3),
      contempt: Math.min(1, Math.abs((bs["mouthSmileLeft"] || 0) - (bs["mouthSmileRight"] || 0)) * 2),
      neutral: 0, // computed below
    };

    // Neutral = inverse of max detected emotion
    const maxEmotion = Math.max(...Object.values(emotions));
    emotions.neutral = Math.max(0, 1 - maxEmotion * 1.5);

    // Normalize
    const total = Object.values(emotions).reduce((a, b) => a + b, 0) || 1;
    for (const k of Object.keys(emotions)) {
      emotions[k] = Math.round((emotions[k] / total) * 1000) / 1000;
    }

    // Find dominant
    let dominant = "neutral";
    let maxConf = 0;
    for (const [k, v] of Object.entries(emotions)) {
      if (v > maxConf) {
        maxConf = v;
        dominant = k;
      }
    }

    return { label: dominant, confidence: maxConf, all: emotions };
  }

  _emotionFromGeometry(landmarks) {
    // Simple geometric heuristics when blendshapes aren't available
    const mouthWidth =
      Math.abs(landmarks[RIGHT_MOUTH].x - landmarks[LEFT_MOUTH].x);
    const mouthHeight =
      Math.abs(landmarks[LOWER_LIP].y - landmarks[UPPER_LIP].y);
    const mouthRatio = mouthHeight / (mouthWidth || 0.001);

    const leftBrowHeight =
      landmarks[LEFT_EYE_TOP].y - landmarks[LEFT_EYEBROW_INNER].y;
    const rightBrowHeight =
      landmarks[RIGHT_EYE_TOP].y - landmarks[RIGHT_EYEBROW_INNER].y;
    const browHeight = (leftBrowHeight + rightBrowHeight) / 2;

    const leftEyeOpen =
      Math.abs(landmarks[LEFT_EYE_TOP].y - landmarks[LEFT_EYE_BOTTOM].y);
    const rightEyeOpen =
      Math.abs(landmarks[RIGHT_EYE_TOP].y - landmarks[RIGHT_EYE_BOTTOM].y);
    const eyeOpenness = (leftEyeOpen + rightEyeOpen) / 2;

    // Mouth corners relative to center
    const mouthCenterY = (landmarks[UPPER_LIP].y + landmarks[LOWER_LIP].y) / 2;
    const leftCornerUp = mouthCenterY - landmarks[LEFT_MOUTH].y;
    const rightCornerUp = mouthCenterY - landmarks[RIGHT_MOUTH].y;
    const smileScore = (leftCornerUp + rightCornerUp) / 2;

    let label = "neutral";
    let confidence = 0.5;

    if (smileScore > 0.01 && mouthRatio > 0.15) {
      label = "happiness";
      confidence = Math.min(0.9, 0.5 + smileScore * 10);
    } else if (mouthRatio > 0.4 && browHeight > 0.04) {
      label = "surprise";
      confidence = Math.min(0.85, 0.5 + mouthRatio);
    } else if (smileScore < -0.005) {
      label = "sadness";
      confidence = Math.min(0.7, 0.4 + Math.abs(smileScore) * 8);
    }

    return {
      label,
      confidence,
      all: {
        [label]: confidence,
        neutral: label === "neutral" ? confidence : 1 - confidence,
      },
    };
  }

  // ── No-face handling ──────────────────────────────────────────
  _handleNoFace() {
    const now = performance.now();
    if (this._noFaceStart === null) this._noFaceStart = now;

    // Grace period: return last good result briefly
    if (now - this._noFaceStart < NO_FACE_GRACE_MS && this._lastGoodResult) {
      return this._lastGoodResult;
    }

    this._gazeOffStart = null;
    return {
      posture: "No Face",
      eyeContact: "No Face",
      headPose: { yaw: 0, pitch: 0, roll: 0 },
      gazeRatio: 0.5,
      emotion: "none",
      confidence: 0,
      allEmotions: {},
      hasFace: false,
    };
  }

  _default() {
    return {
      posture: "Initializing",
      eyeContact: "Initializing",
      headPose: { yaw: 0, pitch: 0, roll: 0 },
      gazeRatio: 0.5,
      emotion: "neutral",
      confidence: 0.5,
      allEmotions: { neutral: 1 },
      hasFace: false,
    };
  }

  destroy() {
    if (this.landmarker) {
      this.landmarker.close();
      this.landmarker = null;
    }
    this.ready = false;
  }
}

// Singleton
let _instance = null;

export function getFaceAnalyzer() {
  if (!_instance) {
    _instance = new FaceAnalyzer();
  }
  return _instance;
}

export default FaceAnalyzer;
