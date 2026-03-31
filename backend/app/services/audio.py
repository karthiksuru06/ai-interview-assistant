"""
Audio Processing Service
========================
Real-time audio analysis for voice clarity, fluency, and speech-to-text.
Optimized for interview coaching scenarios.
"""

import asyncio
import base64
import io
import re
import time
from collections import deque
from typing import Dict, List, Optional, Tuple
import threading

import numpy as np

from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AudioMetrics:
    """Container for audio analysis results."""

    def __init__(self):
        self.clarity_score: float = 0.0
        self.fluency_score: float = 0.0
        self.wpm: float = 0.0
        self.silence_ratio: float = 0.0
        self.filler_count: int = 0
        self.volume_level: str = "normal"
        self.is_speaking: bool = False
        self.transcript: str = ""


class VoiceClarityAnalyzer:
    """
    Analyze voice clarity from audio signals.

    Metrics:
    - Signal-to-Noise Ratio (SNR)
    - Amplitude consistency
    - Silence detection
    """

    SILENCE_THRESHOLD = 0.01
    WINDOW_MS = 50  # 50ms analysis windows

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.window_size = int(self.WINDOW_MS / 1000 * sample_rate)

    def analyze(self, audio: np.ndarray) -> Dict:
        """
        Analyze audio chunk for voice clarity.

        Args:
            audio: Audio samples (float32, normalized to [-1, 1])

        Returns:
            Clarity metrics dictionary
        """
        if len(audio) < self.window_size:
            return self._empty_result()

        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
            if np.abs(audio).max() > 1.0:
                audio = audio / 32768.0  # Normalize int16 range

        # Calculate RMS amplitude
        rms = np.sqrt(np.mean(audio ** 2))

        # Detect silence
        silence_frames = np.sum(np.abs(audio) < self.SILENCE_THRESHOLD)
        silence_ratio = silence_frames / len(audio)

        # Calculate window-based metrics
        windows = [
            audio[i:i + self.window_size]
            for i in range(0, len(audio) - self.window_size, self.window_size // 2)
        ]

        if not windows:
            return self._empty_result()

        window_rms = np.array([np.sqrt(np.mean(w ** 2)) for w in windows])

        # Amplitude variance (consistency)
        amplitude_mean = np.mean(window_rms)
        amplitude_var = np.var(window_rms)
        cv = amplitude_var / (amplitude_mean + 1e-8)  # Coefficient of variation

        # Estimate SNR
        sorted_rms = np.sort(window_rms)
        noise_floor = np.mean(sorted_rms[:max(1, len(sorted_rms) // 10)])
        signal_peak = np.mean(sorted_rms[-max(1, len(sorted_rms) // 10):])
        snr_db = 20 * np.log10((signal_peak + 1e-8) / (noise_floor + 1e-8))

        # Calculate scores
        snr_score = min(100, max(0, (snr_db - 5) / 15 * 100))
        silence_score = max(0, (1 - silence_ratio / 0.5)) * 100
        consistency_score = max(0, (1 - cv / 2)) * 100

        clarity_score = (
            0.4 * snr_score +
            0.3 * silence_score +
            0.3 * consistency_score
        )

        # Determine volume level
        if rms < 0.02:
            volume_level = "low"
        elif rms < 0.15:
            volume_level = "normal"
        else:
            volume_level = "high"

        return {
            'clarity_score': round(clarity_score, 1),
            'snr_db': round(snr_db, 1),
            'snr_score': round(snr_score, 1),
            'silence_ratio': round(silence_ratio, 3),
            'silence_score': round(silence_score, 1),
            'consistency_score': round(consistency_score, 1),
            'rms_amplitude': round(rms, 4),
            'volume_level': volume_level,
            'is_speaking': silence_ratio < 0.7
        }

    def _empty_result(self) -> Dict:
        return {
            'clarity_score': 0.0,
            'snr_db': 0.0,
            'snr_score': 0.0,
            'silence_ratio': 1.0,
            'silence_score': 0.0,
            'consistency_score': 0.0,
            'rms_amplitude': 0.0,
            'volume_level': 'silent',
            'is_speaking': False
        }


class FluencyAnalyzer:
    """
    Analyze speech fluency from transcripts.

    Metrics:
    - Words per minute (WPM)
    - Filler word detection
    - Sentence structure
    """

    FILLER_PATTERNS = [
        r'\bum+\b', r'\buh+\b', r'\blike\b', r'\byou know\b',
        r'\bbasically\b', r'\bactually\b', r'\bso\b', r'\bright\b',
        r'\bi mean\b', r'\bkind of\b', r'\bsort of\b', r'\bwell\b'
    ]

    OPTIMAL_WPM_MIN = 120
    OPTIMAL_WPM_MAX = 150

    def __init__(self):
        self.word_history: deque = deque(maxlen=100)
        self.time_history: deque = deque(maxlen=100)

    def analyze(
        self,
        transcript: str,
        duration_seconds: float,
        word_timestamps: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Analyze transcript for fluency metrics.

        Args:
            transcript: Transcribed text
            duration_seconds: Duration of audio
            word_timestamps: Optional list of {word, start, end}

        Returns:
            Fluency metrics dictionary
        """
        if not transcript or duration_seconds < 0.1:
            return self._empty_result()

        words = transcript.split()
        word_count = len(words)
        duration_minutes = duration_seconds / 60

        # Calculate WPM
        wpm = word_count / max(0.1, duration_minutes)

        # WPM score
        wpm_score = self._calculate_wpm_score(wpm)

        # Filler word analysis
        filler_result = self._detect_fillers(transcript)

        # Pause analysis
        pause_score = 70.0  # Default
        pause_stats = {}

        if word_timestamps and len(word_timestamps) > 1:
            pause_result = self._analyze_pauses(word_timestamps)
            pause_score = pause_result['score']
            pause_stats = pause_result['stats']

        # Sentence structure
        structure_score = self._analyze_structure(transcript)

        # Combined fluency score
        fluency_score = (
            0.35 * wpm_score +
            0.25 * pause_score +
            0.20 * structure_score +
            0.20 * filler_result['score']
        )

        # Determine feedback
        pace_feedback = self._get_pace_feedback(wpm)

        return {
            'fluency_score': round(fluency_score, 1),
            'wpm': round(wpm, 1),
            'wpm_score': round(wpm_score, 1),
            'pause_score': round(pause_score, 1),
            'structure_score': round(structure_score, 1),
            'filler_score': round(filler_result['score'], 1),
            'filler_count': filler_result['count'],
            'filler_ratio': round(filler_result['ratio'], 2),
            'fillers_found': filler_result['found'],
            'word_count': word_count,
            'pause_stats': pause_stats,
            'pace_feedback': pace_feedback
        }

    def _calculate_wpm_score(self, wpm: float) -> float:
        """Calculate WPM score based on optimal range."""
        if self.OPTIMAL_WPM_MIN <= wpm <= self.OPTIMAL_WPM_MAX:
            return 100.0
        elif 100 <= wpm < self.OPTIMAL_WPM_MIN or self.OPTIMAL_WPM_MAX < wpm <= 180:
            return 80.0
        elif 80 <= wpm < 100 or 180 < wpm <= 200:
            return 60.0
        else:
            deviation = abs(wpm - 135)
            return max(0, 40 - deviation / 2)

    def _detect_fillers(self, transcript: str) -> Dict:
        """Detect filler words in transcript."""
        transcript_lower = transcript.lower()
        word_count = len(transcript.split())

        filler_count = 0
        fillers_found = []

        for pattern in self.FILLER_PATTERNS:
            matches = re.findall(pattern, transcript_lower)
            filler_count += len(matches)
            fillers_found.extend(matches)

        filler_ratio = (filler_count / max(1, word_count)) * 100
        filler_score = max(0, (1 - filler_ratio / 10)) * 100

        return {
            'score': filler_score,
            'count': filler_count,
            'ratio': filler_ratio,
            'found': fillers_found[:10]
        }

    def _analyze_pauses(self, word_timestamps: List[Dict]) -> Dict:
        """Analyze pause patterns from word timestamps."""
        pauses = []

        for i in range(1, len(word_timestamps)):
            gap = word_timestamps[i]['start'] - word_timestamps[i - 1]['end']
            if gap > 0.1:
                pauses.append(gap)

        if not pauses:
            return {'score': 85.0, 'stats': {}}

        avg_pause = sum(pauses) / len(pauses)
        long_pauses = sum(1 for p in pauses if p > 1.0)

        score = max(0, 100 - long_pauses * 10 - (avg_pause - 0.3) * 50)

        return {
            'score': score,
            'stats': {
                'count': len(pauses),
                'avg_duration': round(avg_pause, 2),
                'long_pauses': long_pauses,
                'max_pause': round(max(pauses), 2)
            }
        }

    def _analyze_structure(self, transcript: str) -> float:
        """Analyze sentence structure quality."""
        sentences = re.split(r'[.!?]+', transcript)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 50.0

        complete = sum(1 for s in sentences if len(s.split()) >= 3)
        ratio = complete / len(sentences)

        return ratio * 100

    def _get_pace_feedback(self, wpm: float) -> str:
        """Generate pace feedback based on WPM."""
        if wpm < 100:
            return "Consider speaking slightly faster to maintain engagement"
        elif wpm > 180:
            return "Try to slow down for better clarity and comprehension"
        elif wpm < 120:
            return "Pace is acceptable, but slightly faster would be ideal"
        elif wpm > 150:
            return "Pace is good, but slowing down slightly may improve clarity"
        else:
            return "Excellent conversational pace"

    def _empty_result(self) -> Dict:
        return {
            'fluency_score': 0.0,
            'wpm': 0.0,
            'wpm_score': 0.0,
            'pause_score': 0.0,
            'structure_score': 0.0,
            'filler_score': 0.0,
            'filler_count': 0,
            'filler_ratio': 0.0,
            'fillers_found': [],
            'word_count': 0,
            'pause_stats': {},
            'pace_feedback': "No speech detected"
        }


class EmotionalStabilityTracker:
    """
    Track emotional stability over time.

    Measures consistency of emotional presentation during the interview.
    """

    EMOTIONS = [
        'neutral', 'happiness', 'surprise', 'sadness',
        'anger', 'disgust', 'fear', 'contempt'
    ]

    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: Number of frames to track (60 ≈ 2 seconds at 30fps)
        """
        self.window_size = window_size
        self.emotion_history: deque = deque(maxlen=window_size)
        self.confidence_history: deque = deque(maxlen=window_size)

    def update(self, emotion_probs: Dict[str, float]) -> Dict:
        """
        Update tracker with new emotion prediction.

        Args:
            emotion_probs: Dictionary of emotion -> probability

        Returns:
            Current stability metrics
        """
        prob_vector = [emotion_probs.get(e, 0) for e in self.EMOTIONS]
        confidence = max(prob_vector)

        self.emotion_history.append(prob_vector)
        self.confidence_history.append(confidence)

        return self.calculate_stability()

    def calculate_stability(self) -> Dict:
        """Calculate emotional stability metrics."""
        if len(self.emotion_history) < 10:
            return {
                'stability_score': 50.0,
                'transition_rate': 0.0,
                'dominant_emotion': 'neutral',
                'confidence_mean': 0.5,
                'status': 'insufficient_data'
            }

        history = list(self.emotion_history)

        # Calculate transition rate
        dominant_emotions = [
            self.EMOTIONS[np.argmax(h)] for h in history
        ]
        transitions = sum(
            1 for i in range(1, len(dominant_emotions))
            if dominant_emotions[i] != dominant_emotions[i - 1]
        )
        transition_rate = transitions / (len(dominant_emotions) - 1)
        transition_score = max(0, (1 - transition_rate / 0.5)) * 100

        # Calculate distribution entropy
        mean_probs = np.mean(history, axis=0)
        entropy = -np.sum(mean_probs * np.log(mean_probs + 1e-8))
        normalized_entropy = entropy / 2.08
        distribution_score = (1 - normalized_entropy) * 100

        # Confidence stability
        confidences = list(self.confidence_history)
        confidence_mean = np.mean(confidences)
        confidence_std = np.std(confidences)
        confidence_score = confidence_mean * 100 * (1 - min(1, confidence_std / 0.3))

        # Combined score
        stability_score = (
            0.4 * transition_score +
            0.3 * distribution_score +
            0.3 * confidence_score
        )

        # Most frequent emotion
        from collections import Counter
        dominant_emotion = Counter(dominant_emotions).most_common(1)[0][0]

        return {
            'stability_score': round(stability_score, 1),
            'transition_rate': round(transition_rate, 3),
            'transition_score': round(transition_score, 1),
            'distribution_score': round(distribution_score, 1),
            'confidence_stability': round(confidence_score, 1),
            'dominant_emotion': dominant_emotion,
            'confidence_mean': round(confidence_mean, 3),
            'emotion_distribution': {
                e: round(float(mean_probs[i]), 3)
                for i, e in enumerate(self.EMOTIONS)
            }
        }

    def reset(self):
        """Reset tracker for new session."""
        self.emotion_history.clear()
        self.confidence_history.clear()


class AudioService:
    """
    Main audio processing service.

    Coordinates voice clarity analysis, fluency tracking, and
    optional speech-to-text transcription.
    """

    _instance: Optional["AudioService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AudioService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, sample_rate: int = 16000):
        if self._initialized:
            return

        self._initialized = True
        self.sample_rate = sample_rate

        # Initialize analyzers
        self.clarity_analyzer = VoiceClarityAnalyzer(sample_rate)
        self.fluency_analyzer = FluencyAnalyzer()
        self.stability_tracker = EmotionalStabilityTracker()

        # Statistics
        self.total_chunks_processed = 0
        self.total_processing_time = 0.0

        # ASR model (lazy load)
        self._asr_model = None
        self._asr_available = False

        logger.info(f"[AUDIO] Service initialized (sample_rate={sample_rate})")

        # Clean up orphaned temp files from previous crashes
        self._cleanup_stale_temp_files()

    @staticmethod
    def _cleanup_stale_temp_files():
        """Remove leftover .webm / .wav temp files from prior sessions."""
        import tempfile, os, glob, time as _t
        tmp_dir = tempfile.gettempdir()
        cutoff = _t.time() - 3600  # older than 1 hour
        for pattern in ("tmp*.webm", "tmp*.wav"):
            for path in glob.glob(os.path.join(tmp_dir, pattern)):
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.unlink(path)
                except OSError:
                    pass

    def _load_asr_model(self) -> bool:
        """Lazy load ASR model (Whisper)."""
        if self._asr_model is not None:
            return self._asr_available

        try:
            import whisper
            self._asr_model = whisper.load_model("small")
            self._asr_available = True
            logger.info("[AUDIO] Whisper ASR model loaded")
            return True
        except ImportError:
            logger.warning("[AUDIO] Whisper not installed - transcription disabled. Install with: pip install openai-whisper")
            return False
        except Exception as e:
            logger.error(f"[AUDIO] Failed to load Whisper: {e}")
            return False

    def decode_base64_audio(self, base64_string: str) -> np.ndarray:
        """
        Decode Base64 audio to numpy array.

        Args:
            base64_string: Base64 encoded audio (PCM int16 or float32)

        Returns:
            Audio samples as float32 numpy array
        """
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]

        audio_bytes = base64.b64decode(base64_string)
        audio = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert to float32 [-1, 1]
        audio = audio.astype(np.float32) / 32768.0

        return audio

    def analyze_chunk(
        self,
        audio: np.ndarray,
        transcribe: bool = False
    ) -> Dict:
        """
        Analyze an audio chunk.

        Args:
            audio: Audio samples (float32, mono, 16kHz)
            transcribe: Whether to run speech-to-text

        Returns:
            Analysis results dictionary
        """
        start_time = time.perf_counter()

        # Voice clarity analysis
        clarity_result = self.clarity_analyzer.analyze(audio)

        result = {
            'success': True,
            'clarity': clarity_result,
            'transcript': None,
            'fluency': None,
            'processing_time_ms': 0
        }

        # Optional transcription
        if transcribe and clarity_result['is_speaking']:
            transcript_result = self._transcribe(audio)
            if transcript_result:
                result['transcript'] = transcript_result['text']

                # Fluency analysis
                duration = len(audio) / self.sample_rate
                fluency_result = self.fluency_analyzer.analyze(
                    transcript_result['text'],
                    duration,
                    transcript_result.get('word_timestamps')
                )
                result['fluency'] = fluency_result

        # Update statistics
        processing_time = (time.perf_counter() - start_time) * 1000
        result['processing_time_ms'] = round(processing_time, 2)

        self.total_chunks_processed += 1
        self.total_processing_time += processing_time

        return result

    def analyze_from_base64(
        self,
        base64_audio: str,
        transcribe: bool = False
    ) -> Dict:
        """Analyze Base64 encoded audio (handles both raw PCM and webm/opus)."""
        try:
            # Check for WebM/EBML header (1A 45 DF A3)
            # We strictly assume frontend sends WebM if header is present.
            if "base64," in base64_audio:
                header_check = base64_audio.split("base64,")[1][:20]
            else:
                header_check = base64_audio[:20]
            
            raw_header = base64.b64decode(header_check)
            is_webm = raw_header.startswith(b'\x1a\x45\xdf\xa3')

            if is_webm:
                # Decode WebM → PCM via ffmpeg so we can run clarity analysis
                pcm_audio = self._decode_webm_to_pcm(base64_audio)
                clarity = (
                    self.clarity_analyzer.analyze(pcm_audio)
                    if pcm_audio is not None and len(pcm_audio) > 0
                    else self.clarity_analyzer._empty_result()
                )

                transcript_text = None
                fluency = None
                if transcribe:
                    transcript_text = self._transcribe_from_base64(base64_audio)
                    if transcript_text and pcm_audio is not None:
                        duration = len(pcm_audio) / self.sample_rate
                        fluency = self.fluency_analyzer.analyze(
                            transcript_text, duration
                        )

                return {
                    'success': True,
                    'clarity': clarity,
                    'transcript': transcript_text,
                    'fluency': fluency,
                    'processing_time_ms': 0,
                }

            # Otherwise, treat as PCM
            audio = self.decode_base64_audio(base64_audio)
            result = self.analyze_chunk(audio, transcribe)
            return result

        except Exception as e:
            print(f"[AUDIO] Analysis failed: {e}")
            # Fallback
            result = {
                'success': True,
                'clarity': self.clarity_analyzer._empty_result(),
                'transcript': None,
                'fluency': None,
                'processing_time_ms': 0,
                'error': str(e)
            }
            if transcribe:
                 # Last ditch attempt
                 try:
                    transcript_text = self._transcribe_from_base64(base64_audio)
                    if transcript_text:
                        result['transcript'] = transcript_text
                 except: 
                     pass
            return result

    _ffmpeg_available: Optional[bool] = None

    @classmethod
    def _check_ffmpeg(cls) -> bool:
        """Check if ffmpeg is available on the system PATH."""
        if cls._ffmpeg_available is not None:
            return cls._ffmpeg_available
        import shutil
        cls._ffmpeg_available = shutil.which("ffmpeg") is not None
        if not cls._ffmpeg_available:
            logger.warning(
                "[AUDIO] WARNING: ffmpeg not found on PATH. "
                "WebM audio decoding and clarity analysis will be disabled. "
                "Install ffmpeg: https://ffmpeg.org/download.html"
            )
        return cls._ffmpeg_available

    def _decode_webm_to_pcm(self, base64_audio: str) -> Optional[np.ndarray]:
        """Decode WebM/Opus base64 audio to raw PCM float32 via ffmpeg."""
        if not self._check_ffmpeg():
            return None  # Gracefully skip — Whisper will handle decoding separately

        import tempfile
        import os
        import subprocess

        if "base64," in base64_audio:
            base64_audio = base64_audio.split("base64,")[1]

        audio_bytes = base64.b64decode(base64_audio)
        tmp_in = None
        tmp_out = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                tmp_in = f.name

            tmp_out = tmp_in.replace(".webm", ".wav")
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", tmp_in,
                    "-ar", str(self.sample_rate),
                    "-ac", "1",
                    "-f", "wav",
                    tmp_out,
                ],
                capture_output=True, timeout=15,
            )

            if result.returncode != 0:
                logger.error(f"[AUDIO] ffmpeg failed: {result.stderr.decode()[:200]}")
                return None

            if os.path.exists(tmp_out):
                import wave
                with wave.open(tmp_out, "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    return audio
            return None
        except FileNotFoundError:
            logger.warning("[AUDIO] ffmpeg not found — install it for WebM audio support")
            self.__class__._ffmpeg_available = False
            return None
        except Exception as e:
            logger.error(f"[AUDIO] WebM→PCM decode failed: {e}")
            return None
        finally:
            for p in (tmp_in, tmp_out):
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    def _transcribe_from_base64(self, base64_audio: str) -> Optional[str]:
        """
        Transcribe audio from base64, handling webm/opus and other formats.
        Saves to a temp file so Whisper (via ffmpeg) can decode any format.
        """
        if not self._load_asr_model():
            return None

        import tempfile
        import os

        if "base64," in base64_audio:
            base64_audio = base64_audio.split("base64,")[1]

        audio_bytes = base64.b64decode(base64_audio)

        # Save to temp file — Whisper uses ffmpeg internally to decode
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            result = self._asr_model.transcribe(temp_path, language="en")
            text = result.get('text', '').strip()
            return text if text else None
        except Exception as e:
            logger.error(f"[AUDIO] File-based transcription error: {e}")
            return None
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _transcribe(self, audio: np.ndarray) -> Optional[Dict]:
        """Transcribe audio using Whisper."""
        if not self._load_asr_model():
            return None

        try:
            # Whisper expects float32 audio
            result = self._asr_model.transcribe(
                audio,
                language="en",
                word_timestamps=True
            )

            # Extract word timestamps
            word_timestamps = []
            for segment in result.get('segments', []):
                for word_info in segment.get('words', []):
                    word_timestamps.append({
                        'word': word_info['word'],
                        'start': word_info['start'],
                        'end': word_info['end']
                    })

            return {
                'text': result['text'].strip(),
                'word_timestamps': word_timestamps
            }
        except Exception as e:
            print(f"[AUDIO] Transcription error: {e}")
            return None

    def update_emotional_stability(self, emotion_probs: Dict[str, float]) -> Dict:
        """Update emotional stability tracker."""
        return self.stability_tracker.update(emotion_probs)

    def get_status(self) -> Dict:
        """Get service status."""
        avg_time = (
            self.total_processing_time / self.total_chunks_processed
            if self.total_chunks_processed > 0 else 0
        )

        return {
            'sample_rate': self.sample_rate,
            'asr_available': self._asr_available,
            'total_chunks_processed': self.total_chunks_processed,
            'avg_processing_time_ms': round(avg_time, 2)
        }

    def reset_session(self):
        """Reset session-specific state."""
        self.stability_tracker.reset()


# Singleton accessor
_audio_service: Optional[AudioService] = None


def get_audio_service() -> AudioService:
    """Get the singleton audio service instance."""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService()
    return _audio_service
