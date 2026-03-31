"""
Audio Emotion Recognition Model
================================
Bi-directional LSTM architecture for voice emotion classification.
Optimized for real-time inference on NVIDIA RTX 4060.

Input: MFCC features [Batch, Time, 40]
Output: 8 emotion class probabilities
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class AudioLSTM(nn.Module):
    """
    Bi-directional LSTM model for audio emotion recognition.

    Architecture:
    - Input Layer: MFCC features (40 coefficients)
    - 2x Bi-LSTM layers (hidden_size=128)
    - Attention mechanism for temporal weighting
    - Dropout regularization
    - Fully connected classifier
    - Softmax output (8 emotions)

    Emotions: neutral, happiness, surprise, sadness, anger, disgust, fear, contempt
    """

    EMOTION_LABELS = [
        "neutral", "happiness", "surprise", "sadness",
        "anger", "disgust", "fear", "contempt"
    ]

    def __init__(
        self,
        input_size: int = 40,          # MFCC features
        hidden_size: int = 128,         # LSTM hidden dimension
        num_layers: int = 2,            # Number of LSTM layers
        num_classes: int = 8,           # Emotion classes
        dropout: float = 0.3,           # Dropout probability
        bidirectional: bool = True,     # Use bidirectional LSTM
        use_attention: bool = True      # Use attention mechanism
    ):
        """
        Initialize AudioLSTM model.

        Args:
            input_size: Number of input features (MFCC coefficients)
            hidden_size: LSTM hidden state dimension
            num_layers: Number of stacked LSTM layers
            num_classes: Number of output classes
            dropout: Dropout probability
            bidirectional: Whether to use bidirectional LSTM
            use_attention: Whether to use attention pooling
        """
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.bidirectional = bidirectional
        self.use_attention = use_attention
        self.num_directions = 2 if bidirectional else 1

        # Input normalization
        self.input_norm = nn.LayerNorm(input_size)

        # Bi-directional LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        # Attention mechanism
        lstm_output_size = hidden_size * self.num_directions
        if use_attention:
            self.attention = nn.Sequential(
                nn.Linear(lstm_output_size, hidden_size),
                nn.Tanh(),
                nn.Linear(hidden_size, 1, bias=False)
            )

        # Dropout
        self.dropout = nn.Dropout(dropout)

        # Fully connected classifier
        self.fc = nn.Sequential(
            nn.Linear(lstm_output_size, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize model weights."""
        for name, param in self.lstm.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)
                # Set forget gate bias to 1
                n = param.size(0)
                param.data[n // 4:n // 2].fill_(1.0)

        for module in self.fc.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        lengths: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape [Batch, Time, Features]
               Features = 40 (MFCC coefficients)
            lengths: Optional sequence lengths for masking

        Returns:
            Logits tensor of shape [Batch, num_classes]
        """
        batch_size, seq_len, _ = x.shape

        # Input normalization
        x = self.input_norm(x)

        # Pack sequences if lengths provided (for variable length inputs)
        if lengths is not None:
            x = nn.utils.rnn.pack_padded_sequence(
                x, lengths.cpu(), batch_first=True, enforce_sorted=False
            )

        # LSTM forward
        lstm_out, (hidden, cell) = self.lstm(x)

        # Unpack if packed
        if lengths is not None:
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(
                lstm_out, batch_first=True, total_length=seq_len
            )

        # lstm_out shape: [Batch, Time, hidden_size * num_directions]

        if self.use_attention:
            # Attention-based pooling
            context = self._attention_pooling(lstm_out, lengths)
        else:
            # Simple pooling: concatenate last hidden states from both directions
            if self.bidirectional:
                # hidden shape: [num_layers * 2, Batch, hidden_size]
                forward_hidden = hidden[-2, :, :]   # Last layer, forward
                backward_hidden = hidden[-1, :, :]  # Last layer, backward
                context = torch.cat([forward_hidden, backward_hidden], dim=1)
            else:
                context = hidden[-1, :, :]

        # Dropout
        context = self.dropout(context)

        # Classification
        logits = self.fc(context)

        return logits

    def _attention_pooling(
        self,
        lstm_out: torch.Tensor,
        lengths: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Apply attention mechanism to pool LSTM outputs.

        Args:
            lstm_out: LSTM output [Batch, Time, hidden_size * num_directions]
            lengths: Optional sequence lengths for masking

        Returns:
            Context vector [Batch, hidden_size * num_directions]
        """
        # Compute attention scores
        attn_scores = self.attention(lstm_out).squeeze(-1)  # [Batch, Time]

        # Mask padding positions if lengths provided
        if lengths is not None:
            batch_size, max_len = attn_scores.shape
            mask = torch.arange(max_len, device=attn_scores.device).expand(
                batch_size, max_len
            ) >= lengths.unsqueeze(1)
            attn_scores = attn_scores.masked_fill(mask, float('-inf'))

        # Softmax to get attention weights
        attn_weights = F.softmax(attn_scores, dim=1).unsqueeze(-1)  # [Batch, Time, 1]

        # Weighted sum
        context = torch.sum(lstm_out * attn_weights, dim=1)  # [Batch, hidden_size * 2]

        return context

    def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict emotions with probabilities.

        Args:
            x: Input MFCC features [Batch, Time, 40]

        Returns:
            Tuple of (predicted_classes, probabilities)
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=-1)
            predictions = torch.argmax(probs, dim=-1)

        return predictions, probs

    def get_emotion_label(self, class_idx: int) -> str:
        """Convert class index to emotion label."""
        return self.EMOTION_LABELS[class_idx]

    @property
    def num_parameters(self) -> int:
        """Total number of parameters."""
        return sum(p.numel() for p in self.parameters())

    @property
    def num_trainable_parameters(self) -> int:
        """Number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class AudioCNN_LSTM(nn.Module):
    """
    CNN + LSTM hybrid model for improved feature extraction.

    Uses 1D CNN layers to extract local patterns from MFCCs
    before passing to LSTM for temporal modeling.
    """

    def __init__(
        self,
        input_size: int = 40,
        hidden_size: int = 128,
        num_classes: int = 8,
        dropout: float = 0.3
    ):
        super().__init__()

        # 1D CNN for local feature extraction
        self.conv_layers = nn.Sequential(
            nn.Conv1d(input_size, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Dropout(dropout),

            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Dropout(dropout),

            nn.Conv1d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
        )

        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )

        # Classifier
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input [Batch, Time, Features]

        Returns:
            Logits [Batch, num_classes]
        """
        # Transpose for Conv1d: [Batch, Features, Time]
        x = x.transpose(1, 2)

        # CNN feature extraction
        x = self.conv_layers(x)

        # Transpose back: [Batch, Time, Features]
        x = x.transpose(1, 2)

        # LSTM
        lstm_out, (hidden, _) = self.lstm(x)

        # Use last hidden states
        context = torch.cat([hidden[-2], hidden[-1]], dim=1)

        # Classify
        logits = self.classifier(context)

        return logits


def create_audio_model(
    architecture: str = "lstm",
    num_classes: int = 8,
    device: Optional[torch.device] = None
) -> nn.Module:
    """
    Factory function to create audio model.

    Args:
        architecture: "lstm" or "cnn_lstm"
        num_classes: Number of emotion classes
        device: Target device

    Returns:
        Configured model on device
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if architecture == "lstm":
        model = AudioLSTM(
            input_size=40,
            hidden_size=128,
            num_layers=2,
            num_classes=num_classes,
            dropout=0.3,
            bidirectional=True,
            use_attention=True
        )
    elif architecture == "cnn_lstm":
        model = AudioCNN_LSTM(
            input_size=40,
            hidden_size=128,
            num_classes=num_classes,
            dropout=0.3
        )
    else:
        raise ValueError(f"Unknown architecture: {architecture}")

    model = model.to(device)

    print(f"[MODEL] Architecture: {architecture}")
    print(f"[MODEL] Parameters: {model.num_parameters:,}")
    print(f"[MODEL] Device: {device}")

    return model


if __name__ == "__main__":
    # Test model
    print("=" * 60)
    print("Testing AudioLSTM Model")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Create model
    model = create_audio_model("lstm", device=device)

    # Test input: [Batch=4, Time=100, MFCC=40]
    x = torch.randn(4, 100, 40).to(device)
    print(f"\nInput shape: {x.shape}")

    # Forward pass
    output = model(x)
    print(f"Output shape: {output.shape}")

    # Predict
    preds, probs = model.predict(x)
    print(f"Predictions: {preds}")
    print(f"Probabilities shape: {probs.shape}")

    # Test with variable lengths
    lengths = torch.tensor([100, 80, 60, 40])
    output_masked = model(x, lengths)
    print(f"Output with masking: {output_masked.shape}")

    print("\n[SUCCESS] Model test passed!")
