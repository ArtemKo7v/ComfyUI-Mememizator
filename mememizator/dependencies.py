# Imports Pillow modules or raises a node-specific error.
def require_pillow():
    try:
        from PIL import Image, ImageColor, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for ComfyUI-Mememizator. Install the custom node dependencies first."
        ) from exc

    return Image, ImageColor, ImageDraw, ImageFont


# Imports NumPy or raises a node-specific error.
def require_numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "NumPy is required for ComfyUI-Mememizator. Install the custom node dependencies first."
        ) from exc

    return np


# Imports PyTorch or raises a node-specific error.
def require_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is required for ComfyUI-Mememizator. This node must run inside a ComfyUI environment."
        ) from exc

    return torch


