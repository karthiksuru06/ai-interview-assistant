"""
Audio Emotion Recognition Training Pipeline
============================================
Training loop with Mixed Precision (AMP) optimized for NVIDIA RTX 4060.

Usage:
    python train_audio.py --data ./data/audio_features --epochs 50
"""

import os
import sys
import argparse
import random
import time
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, TensorDataset, random_split
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, OneCycleLR
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm

from audio_model import AudioLSTM, AudioCNN_LSTM, create_audio_model


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Training configuration."""
    # Data
    data_dir: str = "./data/audio_features"
    train_file: str = "train_mfcc.npy"
    train_labels: str = "train_labels.npy"
    val_file: str = "val_mfcc.npy"
    val_labels: str = "val_labels.npy"

    # Model
    architecture: str = "lstm"  # "lstm" or "cnn_lstm"
    input_size: int = 40        # MFCC features
    hidden_size: int = 128
    num_classes: int = 8
    dropout: float = 0.3

    # Training
    batch_size: int = 32
    num_epochs: int = 50
    learning_rate: float = 0.001
    weight_decay: float = 0.0001
    label_smoothing: float = 0.1

    # Optimization
    use_amp: bool = True
    gradient_clip: float = 1.0
    warmup_epochs: int = 5

    # Checkpointing
    checkpoint_dir: str = "./checkpoints"
    save_every: int = 10
    early_stopping_patience: int = 15

    # Hardware
    num_workers: int = 4
    pin_memory: bool = True
    seed: int = 42


# ============================================================================
# Dataset
# ============================================================================

class AudioEmotionDataset(Dataset):
    """
    Dataset for audio emotion recognition.

    Loads pre-extracted MFCC features from .npy files.
    """

    EMOTION_LABELS = [
        "neutral", "happiness", "surprise", "sadness",
        "anger", "disgust", "fear", "contempt"
    ]

    def __init__(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        max_length: Optional[int] = None,
        augment: bool = False
    ):
        """
        Initialize dataset.

        Args:
            features: MFCC features array [N, Time, 40]
            labels: Labels array [N]
            max_length: Pad/truncate to this length
            augment: Apply data augmentation
        """
        self.features = features
        self.labels = labels
        self.max_length = max_length
        self.augment = augment

        # Determine max length from data if not specified
        if self.max_length is None:
            self.max_length = max(f.shape[0] for f in features)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, int]:
        """
        Get a sample.

        Returns:
            Tuple of (features, label, original_length)
        """
        feat = self.features[idx]
        label = self.labels[idx]

        # Get original length before padding
        orig_length = feat.shape[0]

        # Apply augmentation
        if self.augment:
            feat = self._augment(feat)

        # Pad or truncate to max_length
        feat = self._pad_or_truncate(feat)

        return (
            torch.tensor(feat, dtype=torch.float32),
            torch.tensor(label, dtype=torch.long),
            orig_length
        )

    def _pad_or_truncate(self, feat: np.ndarray) -> np.ndarray:
        """Pad or truncate features to max_length."""
        length = feat.shape[0]

        if length > self.max_length:
            # Truncate (take center)
            start = (length - self.max_length) // 2
            feat = feat[start:start + self.max_length]
        elif length < self.max_length:
            # Pad with zeros
            pad_width = ((0, self.max_length - length), (0, 0))
            feat = np.pad(feat, pad_width, mode='constant', constant_values=0)

        return feat

    def _augment(self, feat: np.ndarray) -> np.ndarray:
        """Apply data augmentation."""
        # Time masking
        if random.random() < 0.5:
            t = feat.shape[0]
            mask_len = random.randint(1, min(10, t // 4))
            mask_start = random.randint(0, t - mask_len)
            feat[mask_start:mask_start + mask_len, :] = 0

        # Feature masking
        if random.random() < 0.3:
            f = feat.shape[1]
            mask_len = random.randint(1, min(5, f // 4))
            mask_start = random.randint(0, f - mask_len)
            feat[:, mask_start:mask_start + mask_len] = 0

        # Time shifting
        if random.random() < 0.3:
            shift = random.randint(-5, 5)
            feat = np.roll(feat, shift, axis=0)

        # Gaussian noise
        if random.random() < 0.3:
            noise = np.random.normal(0, 0.01, feat.shape)
            feat = feat + noise

        return feat


def collate_fn(batch):
    """Custom collate function to handle variable length sequences."""
    features, labels, lengths = zip(*batch)

    features = torch.stack(features)
    labels = torch.stack(labels)
    lengths = torch.tensor(lengths, dtype=torch.long)

    return features, labels, lengths


def load_data(config: Config) -> Tuple[DataLoader, DataLoader]:
    """
    Load training and validation data.

    Args:
        config: Training configuration

    Returns:
        Tuple of (train_loader, val_loader)
    """
    data_dir = Path(config.data_dir)

    # Try to load pre-split data
    train_path = data_dir / config.train_file
    val_path = data_dir / config.val_file

    if train_path.exists() and val_path.exists():
        print(f"[DATA] Loading from {data_dir}")

        train_features = np.load(train_path, allow_pickle=True)
        train_labels = np.load(data_dir / config.train_labels)

        val_features = np.load(val_path, allow_pickle=True)
        val_labels = np.load(data_dir / config.val_labels)

    else:
        # Try loading combined data and split
        combined_path = data_dir / "mfcc_features.npy"
        labels_path = data_dir / "labels.npy"

        if combined_path.exists():
            print(f"[DATA] Loading combined data and splitting")

            all_features = np.load(combined_path, allow_pickle=True)
            all_labels = np.load(labels_path)

            # Split 80/20
            n = len(all_labels)
            indices = np.random.permutation(n)
            split_idx = int(0.8 * n)

            train_idx = indices[:split_idx]
            val_idx = indices[split_idx:]

            train_features = all_features[train_idx]
            train_labels = all_labels[train_idx]

            val_features = all_features[val_idx]
            val_labels = all_labels[val_idx]
        else:
            raise FileNotFoundError(
                f"No data found in {data_dir}. Expected:\n"
                f"  - {config.train_file} + {config.train_labels}, or\n"
                f"  - mfcc_features.npy + labels.npy"
            )

    # Determine max sequence length
    max_len = max(
        max(f.shape[0] for f in train_features),
        max(f.shape[0] for f in val_features)
    )
    max_len = min(max_len, 300)  # Cap at 300 frames (~3 seconds at 100fps)

    print(f"[DATA] Max sequence length: {max_len}")
    print(f"[DATA] Train samples: {len(train_labels)}")
    print(f"[DATA] Val samples: {len(val_labels)}")

    # Print class distribution
    unique, counts = np.unique(train_labels, return_counts=True)
    print("[DATA] Class distribution (train):")
    for u, c in zip(unique, counts):
        print(f"  Class {u}: {c}")

    # Create datasets
    train_dataset = AudioEmotionDataset(
        train_features, train_labels,
        max_length=max_len,
        augment=True
    )

    val_dataset = AudioEmotionDataset(
        val_features, val_labels,
        max_length=max_len,
        augment=False
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
        collate_fn=collate_fn,
        drop_last=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
        collate_fn=collate_fn
    )

    return train_loader, val_loader


# ============================================================================
# Training Functions
# ============================================================================

def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def detect_gpu() -> torch.device:
    """Detect GPU and print info."""
    print("=" * 65)
    print("GPU DETECTION")
    print("=" * 65)
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("[WARN] CUDA not available - using CPU")
        return torch.device("cpu")

    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)

    print(f"CUDA Version: {torch.version.cuda}")
    print(f"GPU: {gpu_name}")
    print(f"VRAM: {vram:.1f} GB")

    torch.backends.cudnn.benchmark = True
    print("[OK] cuDNN benchmark enabled")
    print("=" * 65)

    return torch.device("cuda")


class LabelSmoothingLoss(nn.Module):
    """Cross entropy with label smoothing."""

    def __init__(self, num_classes: int, smoothing: float = 0.1):
        super().__init__()
        self.num_classes = num_classes
        self.smoothing = smoothing
        self.confidence = 1.0 - smoothing

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_probs = torch.log_softmax(pred, dim=-1)

        with torch.no_grad():
            true_dist = torch.zeros_like(log_probs)
            true_dist.fill_(self.smoothing / (self.num_classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), self.confidence)

        return torch.mean(torch.sum(-true_dist * log_probs, dim=-1))


class MetricTracker:
    """Track running average of metrics."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.sum = 0
        self.count = 0
        self.avg = 0

    def update(self, val: float, n: int = 1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: GradScaler,
    device: torch.device,
    epoch: int,
    config: Config
) -> Tuple[float, float]:
    """Train for one epoch with AMP."""
    model.train()

    loss_tracker = MetricTracker()
    acc_tracker = MetricTracker()

    pbar = tqdm(loader, desc=f"Epoch {epoch:02d} [Train]", ncols=100)

    for features, labels, lengths in pbar:
        features = features.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        lengths = lengths.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        # Mixed precision forward
        with autocast(enabled=config.use_amp):
            outputs = model(features, lengths)
            loss = criterion(outputs, labels)

        # Mixed precision backward
        scaler.scale(loss).backward()

        # Gradient clipping
        if config.gradient_clip > 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)

        scaler.step(optimizer)
        scaler.update()

        # Calculate accuracy
        with torch.no_grad():
            preds = outputs.argmax(dim=1)
            acc = (preds == labels).float().mean().item()

        loss_tracker.update(loss.item(), features.size(0))
        acc_tracker.update(acc, features.size(0))

        pbar.set_postfix(loss=f"{loss_tracker.avg:.4f}", acc=f"{acc_tracker.avg:.4f}")

    return loss_tracker.avg, acc_tracker.avg


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    epoch: int,
    config: Config
) -> Tuple[float, float]:
    """Validate the model."""
    model.eval()

    loss_tracker = MetricTracker()
    acc_tracker = MetricTracker()

    pbar = tqdm(loader, desc=f"Epoch {epoch:02d} [Val]  ", ncols=100)

    for features, labels, lengths in pbar:
        features = features.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        lengths = lengths.to(device, non_blocking=True)

        with autocast(enabled=config.use_amp):
            outputs = model(features, lengths)
            loss = criterion(outputs, labels)

        preds = outputs.argmax(dim=1)
        acc = (preds == labels).float().mean().item()

        loss_tracker.update(loss.item(), features.size(0))
        acc_tracker.update(acc, features.size(0))

        pbar.set_postfix(loss=f"{loss_tracker.avg:.4f}", acc=f"{acc_tracker.avg:.4f}")

    return loss_tracker.avg, acc_tracker.avg


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    scaler: GradScaler,
    epoch: int,
    val_acc: float,
    path: str,
    config: Config
) -> None:
    """Save model checkpoint."""
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "scaler_state_dict": scaler.state_dict(),
        "val_acc": val_acc,
        "config": {
            "architecture": config.architecture,
            "input_size": config.input_size,
            "hidden_size": config.hidden_size,
            "num_classes": config.num_classes,
            "dropout": config.dropout
        }
    }
    torch.save(checkpoint, path)


def train(config: Config) -> None:
    """Main training function."""
    # Setup
    device = detect_gpu()
    set_seed(config.seed)

    # Paths
    checkpoint_dir = Path(config.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"audio_{config.architecture}_{timestamp}"

    print("\n" + "=" * 65)
    print("TRAINING CONFIG")
    print("=" * 65)
    print(f"Architecture: {config.architecture}")
    print(f"Batch Size: {config.batch_size}")
    print(f"Learning Rate: {config.learning_rate}")
    print(f"Epochs: {config.num_epochs}")
    print(f"AMP Enabled: {config.use_amp}")
    print("=" * 65 + "\n")

    # Load data
    print("[DATA] Loading datasets...")
    train_loader, val_loader = load_data(config)

    # Create model
    print("\n[MODEL] Creating model...")
    model = create_audio_model(
        architecture=config.architecture,
        num_classes=config.num_classes,
        device=device
    )

    # Loss function
    criterion = LabelSmoothingLoss(
        num_classes=config.num_classes,
        smoothing=config.label_smoothing
    )

    # Optimizer
    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )

    # Scheduler
    total_steps = len(train_loader) * config.num_epochs
    scheduler = OneCycleLR(
        optimizer,
        max_lr=config.learning_rate,
        total_steps=total_steps,
        pct_start=0.1,
        anneal_strategy='cos'
    )

    # AMP Scaler
    scaler = GradScaler(enabled=config.use_amp)

    # Training state
    best_val_acc = 0.0
    patience_counter = 0

    print("\n" + "=" * 65)
    print("TRAINING START")
    print("=" * 65 + "\n")

    for epoch in range(1, config.num_epochs + 1):
        # Train
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer,
            scaler, device, epoch, config
        )

        # Update scheduler (per step, but we call it per epoch for simplicity)
        # scheduler.step()

        # Validate
        val_loss, val_acc = validate(
            model, val_loader, criterion, device, epoch, config
        )

        # Current LR
        lr = optimizer.param_groups[0]['lr']

        # Print summary
        print(f"\n  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f}")
        print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.4f}")
        print(f"  LR: {lr:.6f}")

        if device.type == "cuda":
            vram = torch.cuda.max_memory_allocated() / (1024**3)
            print(f"  Peak VRAM: {vram:.2f} GB")

        # Checkpointing
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0

            best_path = checkpoint_dir / "audio_best.pth"
            save_checkpoint(
                model, optimizer, scheduler, scaler,
                epoch, val_acc, str(best_path), config
            )
            print(f"  [BEST] Saved: {best_path}")
        else:
            patience_counter += 1

        # Periodic checkpoint
        if epoch % config.save_every == 0:
            ckpt_path = checkpoint_dir / f"{run_name}_epoch{epoch}.pth"
            save_checkpoint(
                model, optimizer, scheduler, scaler,
                epoch, val_acc, str(ckpt_path), config
            )

        print("-" * 65)

        # Early stopping
        if patience_counter >= config.early_stopping_patience:
            print(f"\n[STOP] No improvement for {patience_counter} epochs")
            break

    print("\n" + "=" * 65)
    print("TRAINING COMPLETE")
    print("=" * 65)
    print(f"Best Val Accuracy: {best_val_acc:.4f}")
    print(f"Best Model: {checkpoint_dir / 'audio_best.pth'}")


def main():
    parser = argparse.ArgumentParser(description="Audio Emotion Recognition Training")

    parser.add_argument("--data", type=str, default="./data/audio_features",
                        help="Path to audio features directory")
    parser.add_argument("--arch", type=str, default="lstm",
                        choices=["lstm", "cnn_lstm"],
                        help="Model architecture")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001,
                        help="Learning rate")
    parser.add_argument("--no-amp", action="store_true",
                        help="Disable mixed precision training")

    args = parser.parse_args()

    config = Config()
    config.data_dir = args.data
    config.architecture = args.arch
    config.num_epochs = args.epochs
    config.batch_size = args.batch_size
    config.learning_rate = args.lr
    config.use_amp = not args.no_amp

    train(config)


if __name__ == "__main__":
    main()
