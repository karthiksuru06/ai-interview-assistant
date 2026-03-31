#!/usr/bin/env python3
"""
Keras-to-PyTorch Model Converter
==================================
Converts face_classification repo's pretrained Keras FER models
to PyTorch format (.pth) compatible with the project's InferenceService.

Usage:
    python scripts/convert_keras_model.py

This will:
1. Load the best Keras model (fer2013_mini_XCEPTION.102-0.66.hdf5)
2. Extract weights layer by layer
3. Create a matching PyTorch mini_XCEPTION architecture
4. Transfer weights and save as ./models/best_model.pth

Requirements:
    pip install tensorflow  (one-time, for conversion only)
"""

import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================================
# PyTorch mini_XCEPTION Architecture
# Matches face_classification/src/models/cnn.py mini_XCEPTION exactly
# ============================================================================

class SeparableConv2d(nn.Module):
    """Keras-style SeparableConv2D (depthwise + pointwise)."""

    def __init__(self, in_channels, out_channels, kernel_size=3, padding=1, bias=False):
        super().__init__()
        self.depthwise = nn.Conv2d(
            in_channels, in_channels, kernel_size,
            padding=padding, groups=in_channels, bias=bias
        )
        self.pointwise = nn.Conv2d(in_channels, out_channels, 1, bias=bias)

    def forward(self, x):
        x = self.depthwise(x)
        x = self.pointwise(x)
        return x


class XceptionModule(nn.Module):
    """Single Xception residual module."""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        # Residual path: 1x1 conv + stride 2
        self.residual_conv = nn.Conv2d(in_channels, out_channels, 1, stride=2, bias=False)
        self.residual_bn = nn.BatchNorm2d(out_channels)

        # Main path: SepConv -> BN -> ReLU -> SepConv -> BN -> MaxPool
        self.sep_conv1 = SeparableConv2d(in_channels, out_channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.sep_conv2 = SeparableConv2d(out_channels, out_channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.maxpool = nn.MaxPool2d(3, stride=2, padding=1)

    def forward(self, x):
        residual = self.residual_bn(self.residual_conv(x))

        x = F.relu(self.bn1(self.sep_conv1(x)))
        x = self.bn2(self.sep_conv2(x))
        x = self.maxpool(x)

        return x + residual


class MiniXception(nn.Module):
    """
    PyTorch implementation of face_classification's mini_XCEPTION.
    Input: grayscale (1, 48, 48) or (1, 64, 64)
    Output: 7 emotion classes (fer2013)
    """

    def __init__(self, input_shape=(1, 48, 48), num_classes=7):
        super().__init__()
        in_channels = input_shape[0]

        # Base layers
        self.conv1 = nn.Conv2d(in_channels, 8, 3, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.conv2 = nn.Conv2d(8, 8, 3, bias=False)
        self.bn2 = nn.BatchNorm2d(8)

        # Xception modules
        self.module1 = XceptionModule(8, 16)
        self.module2 = XceptionModule(16, 32)
        self.module3 = XceptionModule(32, 64)
        self.module4 = XceptionModule(64, 128)

        # Output
        self.out_conv = nn.Conv2d(128, num_classes, 3, padding=1)
        self.gap = nn.AdaptiveAvgPool2d(1)

    def forward(self, x):
        # Base
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))

        # Xception modules
        x = self.module1(x)
        x = self.module2(x)
        x = self.module3(x)
        x = self.module4(x)

        # Output
        x = self.out_conv(x)
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        return x


# ============================================================================
# FER Wrapper — adapts 7-class mini_XCEPTION for the project's 8-class system
# ============================================================================

class KerasConvertedFER(nn.Module):
    """
    Wrapper that adapts the 7-class Keras FER model to the project's
    8-class emotion system (adds 'contempt' as zero-weight class).

    Input: RGB (3, 224, 224) — same as project's EfficientNet pipeline
    Output: 8 emotion probabilities
    """

    FER2013_LABELS = ["anger", "disgust", "fear", "happiness", "sadness", "surprise", "neutral"]
    PROJECT_LABELS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt"]

    # Mapping: project_idx -> fer2013_idx (contempt has no mapping)
    LABEL_MAP = {
        0: 6,  # neutral -> fer2013 idx 6
        1: 3,  # happiness -> fer2013 idx 3
        2: 5,  # surprise -> fer2013 idx 5
        3: 4,  # sadness -> fer2013 idx 4
        4: 0,  # anger -> fer2013 idx 0
        5: 1,  # disgust -> fer2013 idx 1
        6: 2,  # fear -> fer2013 idx 2
        7: -1, # contempt -> not in fer2013
    }

    def __init__(self):
        super().__init__()
        self.mini_xception = MiniXception(input_shape=(1, 48, 48), num_classes=7)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: RGB tensor (B, 3, 224, 224) — project format
        Returns:
            logits (B, 8) — 8-class emotion probabilities
        """
        # Convert RGB to grayscale
        gray = 0.299 * x[:, 0] + 0.587 * x[:, 1] + 0.114 * x[:, 2]
        gray = gray.unsqueeze(1)  # (B, 1, 224, 224)

        # Resize to 48x48 (mini_XCEPTION input size)
        gray = F.interpolate(gray, size=(48, 48), mode='bilinear', align_corners=False)

        # Normalize to [-1, 1] (Keras preprocess_input v2)
        gray = gray * 2.0 - 1.0

        # Get 7-class logits from mini_XCEPTION
        logits_7 = self.mini_xception(gray)  # (B, 7)

        # Map to 8-class system (add zero for contempt)
        batch_size = logits_7.size(0)
        logits_8 = torch.zeros(batch_size, 8, device=logits_7.device)

        for proj_idx, fer_idx in self.LABEL_MAP.items():
            if fer_idx >= 0:
                logits_8[:, proj_idx] = logits_7[:, fer_idx]
            else:
                logits_8[:, proj_idx] = -5.0  # Low logit for contempt

        return logits_8

    def load_keras_weights(self, keras_model):
        """Transfer weights from a loaded Keras model to this PyTorch model."""
        keras_layers = keras_model.layers
        pytorch_model = self.mini_xception

        # Helper to transfer Conv2D weights (Keras: HWCN -> PyTorch: NCHW)
        def transfer_conv(pytorch_conv, keras_layer):
            w = keras_layer.get_weights()
            if len(w) > 0:
                weight = np.transpose(w[0], (3, 2, 0, 1))  # HWCN -> NCHW
                pytorch_conv.weight.data = torch.tensor(weight, dtype=torch.float32)
                if len(w) > 1 and pytorch_conv.bias is not None:
                    pytorch_conv.bias.data = torch.tensor(w[1], dtype=torch.float32)

        def transfer_bn(pytorch_bn, keras_layer):
            w = keras_layer.get_weights()
            if len(w) == 4:
                pytorch_bn.weight.data = torch.tensor(w[0], dtype=torch.float32)  # gamma
                pytorch_bn.bias.data = torch.tensor(w[1], dtype=torch.float32)    # beta
                pytorch_bn.running_mean = torch.tensor(w[2], dtype=torch.float32)
                pytorch_bn.running_var = torch.tensor(w[3], dtype=torch.float32)

        def transfer_sepconv(pytorch_sep, keras_layer):
            w = keras_layer.get_weights()
            if len(w) >= 2:
                # Depthwise: Keras (H, W, C, 1) -> PyTorch (C, 1, H, W)
                dw = np.transpose(w[0], (2, 3, 0, 1))
                pytorch_sep.depthwise.weight.data = torch.tensor(dw, dtype=torch.float32)
                # Pointwise: Keras (1, 1, C_in, C_out) -> PyTorch (C_out, C_in, 1, 1)
                pw = np.transpose(w[1], (3, 2, 0, 1))
                pytorch_sep.pointwise.weight.data = torch.tensor(pw, dtype=torch.float32)

        # Map Keras layers by type and position
        conv_layers = [l for l in keras_layers if 'conv2d' in l.__class__.__name__.lower()
                       and 'separable' not in l.__class__.__name__.lower()]
        bn_layers = [l for l in keras_layers if 'batchnorm' in l.__class__.__name__.lower()]
        sep_layers = [l for l in keras_layers if 'separable' in l.__class__.__name__.lower()]

        # Base: conv1, bn1, conv2, bn2
        if len(conv_layers) >= 2:
            transfer_conv(pytorch_model.conv1, conv_layers[0])
            transfer_conv(pytorch_model.conv2, conv_layers[1])

        if len(bn_layers) >= 2:
            transfer_bn(pytorch_model.bn1, bn_layers[0])
            transfer_bn(pytorch_model.bn2, bn_layers[1])

        # Xception modules (4 modules, each has: residual_conv, residual_bn, sep1, bn, sep2, bn)
        # Conv layers: [base_conv1, base_conv2, res1_conv, res2_conv, res3_conv, res4_conv, out_conv]
        modules = [pytorch_model.module1, pytorch_model.module2,
                   pytorch_model.module3, pytorch_model.module4]

        # Residual convs start at conv_layers[2]
        for i, mod in enumerate(modules):
            conv_idx = 2 + i
            if conv_idx < len(conv_layers):
                transfer_conv(mod.residual_conv, conv_layers[conv_idx])

        # BN for residuals: bn_layers[2], [5], [8], [11]
        # BN for sep convs: bn_layers[3,4], [6,7], [9,10], [12,13]
        bn_idx = 2
        for mod in modules:
            if bn_idx < len(bn_layers):
                transfer_bn(mod.residual_bn, bn_layers[bn_idx])
            bn_idx += 1
            if bn_idx < len(bn_layers):
                transfer_bn(mod.bn1, bn_layers[bn_idx])
            bn_idx += 1
            if bn_idx < len(bn_layers):
                transfer_bn(mod.bn2, bn_layers[bn_idx])
            bn_idx += 1

        # Separable convs: 2 per module = 8 total
        sep_idx = 0
        for mod in modules:
            if sep_idx < len(sep_layers):
                transfer_sepconv(mod.sep_conv1, sep_layers[sep_idx])
            sep_idx += 1
            if sep_idx < len(sep_layers):
                transfer_sepconv(mod.sep_conv2, sep_layers[sep_idx])
            sep_idx += 1

        # Output conv (last conv layer)
        out_conv_idx = 2 + len(modules)
        if out_conv_idx < len(conv_layers):
            transfer_conv(pytorch_model.out_conv, conv_layers[out_conv_idx])

        print(f"[CONVERT] Transferred weights from {len(conv_layers)} conv, "
              f"{len(bn_layers)} bn, {len(sep_layers)} sep_conv layers")


def convert_keras_to_pytorch(
    keras_model_path: str,
    output_path: str = "./models/best_model.pth"
):
    """
    Convert a Keras FER model to PyTorch format.

    Args:
        keras_model_path: Path to .hdf5 Keras model
        output_path: Path for output .pth file
    """
    print(f"\n{'='*60}")
    print("Keras → PyTorch FER Model Converter")
    print(f"{'='*60}\n")

    # Load Keras model
    try:
        import tensorflow as tf
        print(f"[1/4] Loading Keras model: {keras_model_path}")
        keras_model = tf.keras.models.load_model(keras_model_path, compile=False)
        keras_model.summary()
    except ImportError:
        print("ERROR: TensorFlow is required for conversion.")
        print("Install: pip install tensorflow")
        print("\nAlternatively, the blendshape-based FER fallback works without any model file.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load Keras model: {e}")
        sys.exit(1)

    # Create PyTorch model and transfer weights
    print(f"\n[2/4] Creating PyTorch model and transferring weights...")
    pytorch_model = KerasConvertedFER()
    pytorch_model.load_keras_weights(keras_model)

    # Validate with dummy input
    print(f"\n[3/4] Validating conversion...")
    pytorch_model.eval()

    # Test with a random image
    dummy = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        output = pytorch_model(dummy)
        probs = F.softmax(output, dim=1).numpy()[0]

    labels = KerasConvertedFER.PROJECT_LABELS
    print("Test output (random input):")
    for label, prob in zip(labels, probs):
        print(f"  {label:12s}: {prob:.4f}")

    # Save checkpoint
    print(f"\n[4/4] Saving to {output_path}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    checkpoint = {
        "model_state_dict": pytorch_model.state_dict(),
        "architecture": "keras_converted_mini_xception",
        "source": keras_model_path,
        "num_classes": 8,
        "input_size": 224,
        "emotion_labels": labels,
        "original_accuracy": "0.66 (fer2013 val)",
        "note": "Converted from face_classification repo mini_XCEPTION model",
    }
    torch.save(checkpoint, output_path)

    file_size = os.path.getsize(output_path) / 1024
    print(f"\nSaved: {output_path} ({file_size:.1f} KB)")
    print("Model is ready for use with the InferenceService!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Find the best Keras model
    script_dir = Path(__file__).parent.parent
    face_class_dir = script_dir.parent.parent / "face_classification"

    keras_model = face_class_dir / "trained_models" / "emotion_models" / "fer2013_mini_XCEPTION.102-0.66.hdf5"

    if not keras_model.exists():
        # Try alternative locations
        for candidate in [
            script_dir / "models" / "fer2013_mini_XCEPTION.102-0.66.hdf5",
            Path("face_classification/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5"),
        ]:
            if candidate.exists():
                keras_model = candidate
                break

    if not keras_model.exists():
        print(f"Keras model not found at {keras_model}")
        print("Provide path as argument: python convert_keras_model.py <path_to.hdf5>")
        if len(sys.argv) > 1:
            keras_model = Path(sys.argv[1])
        else:
            sys.exit(1)

    output = str(script_dir / "models" / "best_model.pth")
    convert_keras_to_pytorch(str(keras_model), output)
