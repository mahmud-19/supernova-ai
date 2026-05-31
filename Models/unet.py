import sys
import os
import torch
import segmentation_models_pytorch as smp

# Ensure backend folder is in sys.path so app submodules are importable by retrain.py
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(_HERE), "backend"))

from app.ml.inference import AttentionUNet, BaseUNet

MODELS = {
    "AttentionUNet": {
        "build": lambda: AttentionUNet(),
        "weight": "attention_unet.pth",
        "state_key": None,
        "strict": True,
    },
    "BaseUNet": {
        "build": lambda: BaseUNet(),
        "weight": "base_unet.pth",
        "state_key": None,
        "strict": True,
    },
    "DeepLabV3": {
        "build": lambda: smp.DeepLabV3Plus(
            encoder_name="resnet50",
            encoder_weights=None,
            in_channels=1,
            classes=1,
            activation=None,
        ),
        "weight": "deeplabv3.pth",
        "state_key": "model_state_dict",
        "strict": True,
    },
    "MobileNetV2": {
        "build": lambda: smp.Unet(
            encoder_name="mobilenet_v2",
            encoder_weights=None,
            in_channels=1,
            classes=1,
            activation=None,
        ),
        "weight": "mobilenetv2.pth",
        "state_key": None,
        "strict": True,
    },
    "MobileNetV3": {
        "build": lambda: smp.Unet(
            encoder_name="timm-mobilenetv3_large_100",
            encoder_weights=None,
            in_channels=1,
            classes=1,
            activation=None,
        ),
        "weight": "mobilenetv3.pth",
        "state_key": "model_state_dict",
        "strict": False,
    },
}
