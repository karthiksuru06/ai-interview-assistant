"""
Audio Data Preparation Script
==============================
Extract MFCC features from audio files for training.

Supports:
- RAVDESS dataset
- CREMA-D dataset
- Custom folder structure

Usage:
    python prepare_audio_data.py --input ./raw_audio --output ./data/audio_features
    python prepare_audio_data.py --sample --output ./data/audio_features
"""

import os
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import random

import numpy as np
from tqdm import tqdm


# Emotion mapping (unified across datasets)
EMOTION_MAP = {
    # RAVDESS codes
    "01": 0,  # neutral
    "02": 0,  # calm -> neutral
    "03": 1,  # happy
    "04": 3,  # sad
    "05": 4,  # angry
    "06": 6,  # fearful
    "07": 5,  # disgust
    "08": 2,  # surprised

    # CREMA-D codes
    "NEU": 0,  # neutral
    "HAP": 1,  # happy
    "SAD": 3,  # sad
    "ANG": 4,  # angry
    "FEA": 6,  # fear
    "DIS": 5,  # disgust

    # Text labels
    "neutral": 0,
    "happiness": 1,
    "happy": 1,
    "surprise": 2,
    "surprised": 2,
    "sadness": 3,
    "sad": 3,
    "anger": 4,
    "angry": 4,
    "disgust": 5,
    "fear": 6,
    "fearful": 6,
    "contempt": 7
}

EMOTION_LABELS = [
    "neutral", "happiness", "surprise", "sadness",
    "anger", "disgust", "fear", "contempt"
]


def extract_mfcc(
    audio_path: str,
    sample_rate: int = 16000,
    n_mfcc: int = 40,
    n_fft: int = 512,
    hop_length: int = 160
) -> Optional[np.ndarray]:
    """
    Extract MFCC features from an audio file.

    Args:
        audio_path: Path to audio file
        sample_rate: Target sample rate
        n_mfcc: Number of MFCC coefficients
        n_fft: FFT window size
        hop_length: Hop length

    Returns:
        MFCC features [Time, n_mfcc] or None if failed
    """
    try:
        import librosa

        # Load audio
        audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)

        # Skip very short audio
        if len(audio) < sample_rate * 0.5:  # Less than 0.5 seconds
            return None

        # Extract MFCC
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=sample_rate,
            n_mfcc=n_mfcc,
            n_fft=n_fft,
            hop_length=hop_length
        )

        # Transpose to [Time, Features]
        return mfcc.T

    except Exception as e:
        print(f"Error processing {audio_path}: {e}")
        return None


def parse_ravdess_filename(filename: str) -> Optional[int]:
    """
    Parse emotion from RAVDESS filename.

    Format: 03-01-05-01-01-01-12.wav
            MM-VV-EE-EI-SS-RR-AA.wav

    EE = Emotion (01=neutral, 02=calm, 03=happy, etc.)
    """
    try:
        parts = filename.replace(".wav", "").split("-")
        emotion_code = parts[2]
        return EMOTION_MAP.get(emotion_code)
    except:
        return None


def parse_cremad_filename(filename: str) -> Optional[int]:
    """
    Parse emotion from CREMA-D filename.

    Format: 1001_DFA_ANG_XX.wav
            ID_SENTENCE_EMOTION_LEVEL.wav
    """
    try:
        parts = filename.replace(".wav", "").split("_")
        emotion_code = parts[2]
        return EMOTION_MAP.get(emotion_code)
    except:
        return None


def parse_folder_structure(audio_path: Path, root: Path) -> Optional[int]:
    """
    Parse emotion from folder structure.

    Expected: root/emotion_name/file.wav
    """
    try:
        emotion_folder = audio_path.parent.name.lower()

        # Try direct mapping
        if emotion_folder in EMOTION_MAP:
            return EMOTION_MAP[emotion_folder]

        # Try with index prefix (e.g., "0_neutral")
        if "_" in emotion_folder:
            emotion_name = emotion_folder.split("_", 1)[1]
            if emotion_name in EMOTION_MAP:
                return EMOTION_MAP[emotion_name]

        return None
    except:
        return None


def process_dataset(
    input_dir: str,
    output_dir: str,
    sample_rate: int = 16000,
    n_mfcc: int = 40,
    val_split: float = 0.2,
    test_split: float = 0.1
) -> Dict[str, int]:
    """
    Process audio dataset and extract MFCC features.

    Args:
        input_dir: Directory containing audio files
        output_dir: Output directory for .npy files
        sample_rate: Target sample rate
        n_mfcc: Number of MFCC coefficients
        val_split: Validation split ratio
        test_split: Test split ratio

    Returns:
        Statistics dictionary
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all audio files
    audio_files = list(input_path.glob("**/*.wav"))
    audio_files.extend(input_path.glob("**/*.mp3"))
    audio_files.extend(input_path.glob("**/*.flac"))

    print(f"[DATA] Found {len(audio_files)} audio files")

    features = []
    labels = []
    skipped = 0

    for audio_path in tqdm(audio_files, desc="Extracting MFCCs"):
        # Try different filename parsers
        filename = audio_path.name

        label = parse_ravdess_filename(filename)
        if label is None:
            label = parse_cremad_filename(filename)
        if label is None:
            label = parse_folder_structure(audio_path, input_path)

        if label is None:
            skipped += 1
            continue

        # Extract MFCC
        mfcc = extract_mfcc(str(audio_path), sample_rate, n_mfcc)

        if mfcc is None:
            skipped += 1
            continue

        features.append(mfcc)
        labels.append(label)

    print(f"[DATA] Processed: {len(labels)}, Skipped: {skipped}")

    if len(labels) == 0:
        print("[ERROR] No valid samples found!")
        return {"error": "No samples"}

    # Convert to arrays
    features = np.array(features, dtype=object)  # Variable length
    labels = np.array(labels, dtype=np.int64)

    # Print class distribution
    print("\n[DATA] Class distribution:")
    unique, counts = np.unique(labels, return_counts=True)
    for u, c in zip(unique, counts):
        print(f"  {EMOTION_LABELS[u]}: {c}")

    # Shuffle
    indices = np.random.permutation(len(labels))
    features = features[indices]
    labels = labels[indices]

    # Split
    n = len(labels)
    test_idx = int(n * (1 - test_split))
    val_idx = int(test_idx * (1 - val_split / (1 - test_split)))

    train_features = features[:val_idx]
    train_labels = labels[:val_idx]

    val_features = features[val_idx:test_idx]
    val_labels = labels[val_idx:test_idx]

    test_features = features[test_idx:]
    test_labels = labels[test_idx:]

    # Save
    np.save(output_path / "train_mfcc.npy", train_features)
    np.save(output_path / "train_labels.npy", train_labels)

    np.save(output_path / "val_mfcc.npy", val_features)
    np.save(output_path / "val_labels.npy", val_labels)

    np.save(output_path / "test_mfcc.npy", test_features)
    np.save(output_path / "test_labels.npy", test_labels)

    stats = {
        "total": len(labels),
        "train": len(train_labels),
        "val": len(val_labels),
        "test": len(test_labels),
        "skipped": skipped
    }

    print(f"\n[DATA] Saved to {output_path}")
    print(f"  Train: {stats['train']}")
    print(f"  Val: {stats['val']}")
    print(f"  Test: {stats['test']}")

    return stats


def create_sample_dataset(
    output_dir: str,
    num_samples: int = 200,
    sequence_length: int = 100,
    n_mfcc: int = 40,
    num_classes: int = 8
) -> None:
    """
    Create a synthetic sample dataset for testing.

    Generates random MFCC-like features with class-specific patterns.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[DATA] Creating sample dataset with {num_samples} samples per class")

    np.random.seed(42)

    all_features = []
    all_labels = []

    for class_idx in range(num_classes):
        for _ in range(num_samples):
            # Random sequence length
            seq_len = random.randint(50, sequence_length)

            # Generate class-specific patterns
            base = np.random.randn(seq_len, n_mfcc).astype(np.float32)

            # Add class-specific bias
            class_bias = np.zeros(n_mfcc)
            class_bias[class_idx * 5:(class_idx + 1) * 5] = 0.5
            base += class_bias

            # Add some structure
            freq = 0.1 + class_idx * 0.02
            time_pattern = np.sin(np.linspace(0, freq * seq_len, seq_len))
            base[:, 0] += time_pattern

            all_features.append(base)
            all_labels.append(class_idx)

    # Convert to arrays
    features = np.array(all_features, dtype=object)
    labels = np.array(all_labels, dtype=np.int64)

    # Shuffle
    indices = np.random.permutation(len(labels))
    features = features[indices]
    labels = labels[indices]

    # Split
    n = len(labels)
    train_idx = int(n * 0.7)
    val_idx = int(n * 0.85)

    # Save
    np.save(output_path / "train_mfcc.npy", features[:train_idx])
    np.save(output_path / "train_labels.npy", labels[:train_idx])

    np.save(output_path / "val_mfcc.npy", features[train_idx:val_idx])
    np.save(output_path / "val_labels.npy", labels[train_idx:val_idx])

    np.save(output_path / "test_mfcc.npy", features[val_idx:])
    np.save(output_path / "test_labels.npy", labels[val_idx:])

    print(f"[DATA] Sample dataset created at {output_path}")
    print(f"  Train: {train_idx}")
    print(f"  Val: {val_idx - train_idx}")
    print(f"  Test: {n - val_idx}")
    print("\n[NOTE] This is synthetic data for pipeline testing only.")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare audio data for emotion recognition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process RAVDESS dataset:
    python prepare_audio_data.py --input ./RAVDESS --output ./data/audio_features

    # Process CREMA-D dataset:
    python prepare_audio_data.py --input ./CREMA-D --output ./data/audio_features

    # Create sample dataset for testing:
    python prepare_audio_data.py --sample --output ./data/audio_features
        """
    )

    parser.add_argument("--input", type=str, help="Input directory with audio files")
    parser.add_argument("--output", type=str, default="./data/audio_features",
                        help="Output directory for features")
    parser.add_argument("--sample", action="store_true",
                        help="Create sample dataset for testing")
    parser.add_argument("--sample-rate", type=int, default=16000,
                        help="Audio sample rate")
    parser.add_argument("--n-mfcc", type=int, default=40,
                        help="Number of MFCC coefficients")

    args = parser.parse_args()

    if args.sample:
        create_sample_dataset(args.output)
    elif args.input:
        process_dataset(
            input_dir=args.input,
            output_dir=args.output,
            sample_rate=args.sample_rate,
            n_mfcc=args.n_mfcc
        )
    else:
        parser.print_help()
        print("\n[ERROR] Specify --input or --sample")


if __name__ == "__main__":
    main()
