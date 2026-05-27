
import os
import numpy as np
import pandas as pd
import cv2
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import segmentation_models_pytorch as smp
import gc


# ========== PATHS ==========
BASE_DIR = r"D:\Capstone project\BUSBRA"
IMG_DIR = os.path.join(BASE_DIR, "Images")
MASK_DIR = os.path.join(BASE_DIR, "Masks")
CSV_PATH = os.path.join(BASE_DIR, "bus_data.csv")

_HERE = os.path.dirname(os.path.abspath(__file__))  # same dir as this script

MODEL_PATHS = {
    'AttentionUNet': os.path.join(_HERE, "attention  unet model", "checkpoints", "best_attention_unet.pth"),
    'BaseUNet':      r"D:\Capstone project\baseUnet\checkpoints_base_unet_github\best_base_unet.pth",
    'DeepLabV3':     os.path.join(_HERE, "DeepLab V3+", "checkpoints", "best_model.pth"),
    'MobileNetV2':   r"D:\Capstone project\mobileNetV2\checkpoints\best_model.pth",
    'MobileNetV3':   os.path.join(_HERE, "MobileVnet3", "best_model.pth"),
}

OUTPUT_DIR = os.path.join(_HERE, "ensemble_uncertainty_results")

IMAGE_SIZE = (256, 256)
BATCH_SIZE = 2  # Small batch for 6GB GPU
RANDOM_SEED = 42


# ========== MODEL ARCHITECTURES ==========

# 1. ATTENTION UNET
def conv_block(in_channels, out_channels, dropout_rate=0.0, batch_norm=True):
    layers = []
    layers.append(nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1))
    if batch_norm:
        layers.append(nn.BatchNorm2d(out_channels))
    layers.append(nn.ReLU(inplace=True))
    layers.append(nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1))
    if batch_norm:
        layers.append(nn.BatchNorm2d(out_channels))
    layers.append(nn.ReLU(inplace=True))
    if dropout_rate > 0:
        layers.append(nn.Dropout2d(dropout_rate))
    return nn.Sequential(*layers)


class AttentionBlock(nn.Module):
    def __init__(self, F_g, F_l, F_int):
        super().__init__()
        self.W_g = nn.Sequential(nn.Conv2d(F_g, F_int, kernel_size=1, stride=1, padding=0, bias=True), nn.BatchNorm2d(F_int))
        self.W_x = nn.Sequential(nn.Conv2d(F_l, F_int, kernel_size=1, stride=1, padding=0, bias=True), nn.BatchNorm2d(F_int))
        self.psi = nn.Sequential(nn.Conv2d(F_int, 1, kernel_size=1, stride=1, padding=0, bias=True), nn.BatchNorm2d(1), nn.Sigmoid())
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, g, x):
        g1 = self.W_g(g)
        x1 = self.W_x(x)
        if g1.size()[2:] != x1.size()[2:]:
            g1 = nn.functional.interpolate(g1, size=x1.size()[2:], mode='bilinear', align_corners=True)
        psi = self.relu(g1 + x1)
        psi = self.psi(psi)
        return x * psi


class AttentionUNet(nn.Module):
    def __init__(self, in_channels=1, num_classes=1, dropout_rate=0.0, batch_norm=True):
        super().__init__()
        F = 64
        self.conv_128 = conv_block(in_channels, F, dropout_rate, batch_norm)
        self.pool_64 = nn.MaxPool2d(2, 2)
        self.conv_64 = conv_block(F, 2*F, dropout_rate, batch_norm)
        self.pool_32 = nn.MaxPool2d(2, 2)
        self.conv_32 = conv_block(2*F, 4*F, dropout_rate, batch_norm)
        self.pool_16 = nn.MaxPool2d(2, 2)
        self.conv_16 = conv_block(4*F, 8*F, dropout_rate, batch_norm)
        self.pool_8 = nn.MaxPool2d(2, 2)
        self.conv_8 = conv_block(8*F, 16*F, dropout_rate, batch_norm)
        self.att_16 = AttentionBlock(16*F, 8*F, 8*F)
        self.att_32 = AttentionBlock(8*F, 4*F, 4*F)
        self.att_64 = AttentionBlock(4*F, 2*F, 2*F)
        self.att_128 = AttentionBlock(2*F, F, F)
        self.up_16 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_16 = conv_block(24*F, 8*F, dropout_rate, batch_norm)
        self.up_32 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_32 = conv_block(12*F, 4*F, dropout_rate, batch_norm)
        self.up_64 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_64 = conv_block(6*F, 2*F, dropout_rate, batch_norm)
        self.up_128 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_128 = conv_block(3*F, F, dropout_rate, batch_norm)
        self.conv_final = nn.Conv2d(F, num_classes, 1)
        self.final_bn = nn.BatchNorm2d(num_classes) if batch_norm else nn.Identity()
    
    def forward(self, x):
        c128 = self.conv_128(x)
        c64 = self.conv_64(self.pool_64(c128))
        c32 = self.conv_32(self.pool_32(c64))
        c16 = self.conv_16(self.pool_16(c32))
        c8 = self.conv_8(self.pool_8(c16))
        u16 = self.up_conv_16(torch.cat([self.up_16(c8), self.att_16(c8, c16)], 1))
        u32 = self.up_conv_32(torch.cat([self.up_32(u16), self.att_32(u16, c32)], 1))
        u64 = self.up_conv_64(torch.cat([self.up_64(u32), self.att_64(u32, c64)], 1))
        u128 = self.up_conv_128(torch.cat([self.up_128(u64), self.att_128(u64, c128)], 1))
        return self.final_bn(self.conv_final(u128))


# 2. BASE UNET — same naming convention as AttentionUNet but no attention gates
class BaseUNet(nn.Module):
    def __init__(self, in_channels=1, num_classes=1, batch_norm=True):
        super().__init__()
        F = 64
        self.conv_128   = conv_block(in_channels, F,    0.0, batch_norm)
        self.pool_64    = nn.MaxPool2d(2, 2)
        self.conv_64    = conv_block(F,    2*F,   0.0, batch_norm)
        self.pool_32    = nn.MaxPool2d(2, 2)
        self.conv_32    = conv_block(2*F,  4*F,   0.0, batch_norm)
        self.pool_16    = nn.MaxPool2d(2, 2)
        self.conv_16    = conv_block(4*F,  8*F,   0.0, batch_norm)
        self.pool_8     = nn.MaxPool2d(2, 2)
        self.conv_8     = conv_block(8*F,  16*F,  0.0, batch_norm)
        self.up_16      = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_16 = conv_block(24*F, 8*F,   0.0, batch_norm)
        self.up_32      = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_32 = conv_block(12*F, 4*F,   0.0, batch_norm)
        self.up_64      = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_64 = conv_block(6*F,  2*F,   0.0, batch_norm)
        self.up_128     = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.up_conv_128= conv_block(3*F,  F,     0.0, batch_norm)
        self.conv_final = nn.Conv2d(F, num_classes, 1)
        self.final_bn   = nn.BatchNorm2d(num_classes)

    def forward(self, x):
        c128 = self.conv_128(x)
        c64  = self.conv_64(self.pool_64(c128))
        c32  = self.conv_32(self.pool_32(c64))
        c16  = self.conv_16(self.pool_16(c32))
        c8   = self.conv_8(self.pool_8(c16))
        u16  = self.up_conv_16(torch.cat([self.up_16(c8),  c16],  1))
        u32  = self.up_conv_32(torch.cat([self.up_32(u16), c32],  1))
        u64  = self.up_conv_64(torch.cat([self.up_64(u32), c64],  1))
        u128 = self.up_conv_128(torch.cat([self.up_128(u64), c128], 1))
        return self.final_bn(self.conv_final(u128))


# ========== DATASET ==========

class BUSBRADataset(Dataset):
    def __init__(self, images_path, masks_path, size=(256, 256)):
        self.images_path = images_path
        self.masks_path = masks_path
        self.size = size
    
    def __len__(self):
        return len(self.images_path)
    
    def __getitem__(self, idx):
        img = cv2.imread(self.images_path[idx], 0)
        msk = cv2.imread(self.masks_path[idx], 0)
        img = cv2.resize(img, self.size).astype(np.float32) / 255.0
        msk = (cv2.resize(msk, self.size, interpolation=cv2.INTER_NEAREST) > 127).astype(np.float32)
        return torch.from_numpy(img[None]), torch.from_numpy(msk[None])


def load_test_data():
    df = pd.read_csv(CSV_PATH)
    cases = df["Case"].unique()
    _, temp = train_test_split(cases, test_size=0.3, random_state=RANDOM_SEED)
    _, test = train_test_split(temp, test_size=0.33, random_state=RANDOM_SEED)
    test_df = df[df["Case"].isin(test)]
    
    test_x, test_y = [], []
    for _, row in test_df.iterrows():
        img_p = os.path.join(IMG_DIR, row["ID"] + ".png")
        msk_p = os.path.join(MASK_DIR, row["ID"].replace("bus_", "mask_") + ".png")
        if os.path.exists(img_p) and os.path.exists(msk_p):
            test_x.append(img_p)
            test_y.append(msk_p)
    
    return test_x, test_y


# ========== LOAD ALL MODELS ==========

def load_all_models(device):
    """Load all 5 trained models."""
    models = {}
    
    print("\n" + "="*70)
    print("LOADING MODELS")
    print("="*70)
    
    # 1. AttentionUNet
    if os.path.exists(MODEL_PATHS['AttentionUNet']):
        try:
            models['AttentionUNet'] = AttentionUNet().to(device)
            models['AttentionUNet'].load_state_dict(torch.load(MODEL_PATHS['AttentionUNet'], map_location=device))
            print("✓ AttentionUNet loaded")
        except Exception as e:
            print(f"✗ AttentionUNet failed: {e}")
    else:
        print(f"✗ AttentionUNet checkpoint not found at: {MODEL_PATHS['AttentionUNet']}")
    
    # 2. BaseUNet
    if os.path.exists(MODEL_PATHS['BaseUNet']):
        try:
            models['BaseUNet'] = BaseUNet().to(device)
            models['BaseUNet'].load_state_dict(torch.load(MODEL_PATHS['BaseUNet'], map_location=device))
            print("✓ BaseUNet loaded")
        except Exception as e:
            print(f"✗ BaseUNet failed: {e}")
    else:
        print(f"✗ BaseUNet checkpoint not found at: {MODEL_PATHS['BaseUNet']}")
    
    # 3. MobileNetV2
    if os.path.exists(MODEL_PATHS['MobileNetV2']):
        try:
            models['MobileNetV2'] = smp.Unet(
                encoder_name='mobilenet_v2',
                encoder_weights=None,
                in_channels=1,
                classes=1,
                activation=None
            ).to(device)
            models['MobileNetV2'].load_state_dict(torch.load(MODEL_PATHS['MobileNetV2'], map_location=device))
            print("✓ MobileNetV2 loaded")
        except Exception as e:
            print(f"✗ MobileNetV2 failed: {e}")
    else:
        print(f"✗ MobileNetV2 checkpoint not found at: {MODEL_PATHS['MobileNetV2']}")
    
    # 4. MobileNetV3
    if os.path.exists(MODEL_PATHS['MobileNetV3']):
        try:
            models['MobileNetV3'] = smp.Unet(
                encoder_name='timm-mobilenetv3_large_100',
                encoder_weights=None,
                in_channels=1,
                classes=1,
                activation=None
            ).to(device)
            state_dict = torch.load(MODEL_PATHS['MobileNetV3'], map_location=device)
            models['MobileNetV3'].load_state_dict(state_dict, strict=False)
            print("✓ MobileNetV3 loaded")
        except Exception as e:
            print(f"✗ MobileNetV3 failed: {e}")
    else:
        print(f"✗ MobileNetV3 checkpoint not found at: {MODEL_PATHS['MobileNetV3']}")
    
    # 5. DeepLabV3+
    if os.path.exists(MODEL_PATHS['DeepLabV3']):
        try:
            models['DeepLabV3'] = smp.DeepLabV3Plus(
                encoder_name='resnet50',
                encoder_weights=None,
                in_channels=1,
                classes=1,
                activation=None
            ).to(device)
            ckpt = torch.load(MODEL_PATHS['DeepLabV3'], map_location=device)
            state = ckpt['model_state_dict'] if isinstance(ckpt, dict) and 'model_state_dict' in ckpt else ckpt
            models['DeepLabV3'].load_state_dict(state)
            print("✓ DeepLabV3+ loaded")
        except Exception as e:
            print(f"✗ DeepLabV3+ failed: {e}")
    else:
        print(f"✗ DeepLabV3+ checkpoint not found at: {MODEL_PATHS['DeepLabV3']}")
    
    print(f"\n{'='*70}")
    print(f"TOTAL MODELS LOADED: {len(models)}/5")
    print(f"{'='*70}\n")
    
    return models


# ========== ENSEMBLE UNCERTAINTY ==========

def compute_ensemble_uncertainty(models, test_loader, device):
    """Compute uncertainty from ensemble of different models."""
    print("\n" + "="*70)
    print("ENSEMBLE UNCERTAINTY - COMBINING ALL MODELS")
    print("="*70)
    print(f"Number of models: {len(models)}")
    
    # Clear GPU memory
    torch.cuda.empty_cache()
    gc.collect()
    
    for model in models.values():
        model.eval()
    
    all_predictions = []
    all_uncertainties = []
    all_masks = []
    all_images = []
    all_individual_preds = {name: [] for name in models.keys()}
    
    for images, masks in tqdm(test_loader, desc='Computing Ensemble'):
        images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)
        
        # Get prediction from each model
        model_preds = []
        with torch.no_grad():
            for name, model in models.items():
                pred = torch.sigmoid(model(images))
                model_preds.append(pred)
                all_individual_preds[name].append(pred.cpu())
        
        # Stack predictions: [num_models, batch, 1, H, W]
        model_preds = torch.stack(model_preds, dim=0)
        
        # Compute mean and variance across models
        mean_pred = model_preds.mean(dim=0)
        variance = model_preds.var(dim=0)
        
        all_predictions.append(mean_pred.cpu())
        all_uncertainties.append(variance.cpu())
        all_masks.append(masks.cpu())
        all_images.append(images.cpu())
        
        # Clear GPU
        del images, masks, model_preds, mean_pred, variance
        torch.cuda.empty_cache()
    
    print("✓ Ensemble uncertainty computed")
    
    return {
        'predictions': all_predictions,
        'uncertainties': all_uncertainties,
        'masks': all_masks,
        'images': all_images,
        'individual_predictions': all_individual_preds
    }


# ========== PERFORMANCE METRICS ==========

def compute_ensemble_metrics(results):
    """Compute detailed performance metrics for ensemble and individual models."""
    print("\n" + "="*70)
    print("COMPUTING PERFORMANCE METRICS")
    print("="*70)
    
    # Initialize metrics storage
    ensemble_metrics = {
        'dice': [], 'iou': [], 'accuracy': [], 
        'precision': [], 'recall': [], 'f1': []
    }
    
    individual_metrics = {
        name: {'dice': [], 'iou': [], 'accuracy': [], 'precision': [], 'recall': [], 'f1': []}
        for name in results['individual_predictions'].keys()
    }
    
    # Compute metrics for each sample
    for batch_idx in range(len(results['predictions'])):
        batch_preds = results['predictions'][batch_idx]
        batch_masks = results['masks'][batch_idx]
        
        for i in range(batch_preds.size(0)):
            pred_mean = batch_preds[i, 0].numpy()
            mask_gt = batch_masks[i, 0].numpy()
            pred_binary = (pred_mean > 0.5).astype(np.float32)
            
            # Flatten for metrics
            pred_flat = pred_binary.flatten()
            mask_flat = mask_gt.flatten()
            
            # Ensemble metrics
            TP = np.sum(pred_flat * mask_flat)
            TN = np.sum((1 - pred_flat) * (1 - mask_flat))
            FP = np.sum(pred_flat * (1 - mask_flat))
            FN = np.sum((1 - pred_flat) * mask_flat)
            
            eps = 1e-8
            dice = 2 * TP / (2 * TP + FP + FN + eps)
            iou = TP / (TP + FP + FN + eps)
            accuracy = (TP + TN) / (TP + TN + FP + FN + eps)
            precision = TP / (TP + FP + eps)
            recall = TP / (TP + FN + eps)
            f1 = 2 * precision * recall / (precision + recall + eps)
            
            ensemble_metrics['dice'].append(dice)
            ensemble_metrics['iou'].append(iou)
            ensemble_metrics['accuracy'].append(accuracy)
            ensemble_metrics['precision'].append(precision)
            ensemble_metrics['recall'].append(recall)
            ensemble_metrics['f1'].append(f1)
            
            # Individual model metrics
            for name in results['individual_predictions'].keys():
                ind_pred = results['individual_predictions'][name][batch_idx][i, 0].numpy()
                ind_binary = (ind_pred > 0.5).astype(np.float32).flatten()
                
                TP = np.sum(ind_binary * mask_flat)
                TN = np.sum((1 - ind_binary) * (1 - mask_flat))
                FP = np.sum(ind_binary * (1 - mask_flat))
                FN = np.sum((1 - ind_binary) * mask_flat)
                
                dice = 2 * TP / (2 * TP + FP + FN + eps)
                iou = TP / (TP + FP + FN + eps)
                accuracy = (TP + TN) / (TP + TN + FP + FN + eps)
                precision = TP / (TP + FP + eps)
                recall = TP / (TP + FN + eps)
                f1 = 2 * precision * recall / (precision + recall + eps)
                
                individual_metrics[name]['dice'].append(dice)
                individual_metrics[name]['iou'].append(iou)
                individual_metrics[name]['accuracy'].append(accuracy)
                individual_metrics[name]['precision'].append(precision)
                individual_metrics[name]['recall'].append(recall)
                individual_metrics[name]['f1'].append(f1)
    
    # Compute averages
    ensemble_avg = {k: np.mean(v) for k, v in ensemble_metrics.items()}
    individual_avg = {
        name: {k: np.mean(v) for k, v in metrics.items()}
        for name, metrics in individual_metrics.items()
    }
    
    # Print results
    print("\n" + "="*70)
    print("ENSEMBLE PERFORMANCE")
    print("="*70)
    print(f"  Dice Score:  {ensemble_avg['dice']:.4f}")
    print(f"  IoU:         {ensemble_avg['iou']:.4f}")
    print(f"  Accuracy:    {ensemble_avg['accuracy']:.4f}")
    print(f"  Precision:   {ensemble_avg['precision']:.4f}")
    print(f"  Recall:      {ensemble_avg['recall']:.4f}")
    print(f"  F1 Score:    {ensemble_avg['f1']:.4f}")
    
    print("\n" + "="*70)
    print("INDIVIDUAL MODEL PERFORMANCE")
    print("="*70)
    for name, metrics in individual_avg.items():
        print(f"\n{name}:")
        print(f"  Dice Score:  {metrics['dice']:.4f}")
        print(f"  IoU:         {metrics['iou']:.4f}")
        print(f"  Accuracy:    {metrics['accuracy']:.4f}")
        print(f"  F1 Score:    {metrics['f1']:.4f}")
    
    return ensemble_avg, individual_avg


def plot_performance_comparison(ensemble_avg, individual_avg, save_dir):
    """Create visual comparison of ensemble vs individual models."""
    
    # Prepare data
    all_models = ['Ensemble'] + list(individual_avg.keys())
    dice_scores = [ensemble_avg['dice']] + [individual_avg[name]['dice'] for name in individual_avg.keys()]
    iou_scores = [ensemble_avg['iou']] + [individual_avg[name]['iou'] for name in individual_avg.keys()]
    f1_scores = [ensemble_avg['f1']] + [individual_avg[name]['f1'] for name in individual_avg.keys()]
    
    # Create comparison plot
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Dice Score
    colors = ['#e74c3c'] + ['#3498db'] * len(individual_avg)
    bars1 = axes[0].bar(all_models, dice_scores, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
    axes[0].set_ylabel('Dice Score', fontsize=12, fontweight='bold')
    axes[0].set_title('Dice Score Comparison', fontsize=14, fontweight='bold')
    axes[0].set_ylim([0, 1])
    axes[0].grid(axis='y', alpha=0.3)
    axes[0].tick_params(axis='x', rotation=45)
    for bar, val in zip(bars1, dice_scores):
        axes[0].text(bar.get_x() + bar.get_width()/2., val + 0.02,
                    f'{val:.3f}', ha='center', fontweight='bold', fontsize=10)
    
    # IoU
    bars2 = axes[1].bar(all_models, iou_scores, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
    axes[1].set_ylabel('IoU Score', fontsize=12, fontweight='bold')
    axes[1].set_title('IoU Score Comparison', fontsize=14, fontweight='bold')
    axes[1].set_ylim([0, 1])
    axes[1].grid(axis='y', alpha=0.3)
    axes[1].tick_params(axis='x', rotation=45)
    for bar, val in zip(bars2, iou_scores):
        axes[1].text(bar.get_x() + bar.get_width()/2., val + 0.02,
                    f'{val:.3f}', ha='center', fontweight='bold', fontsize=10)
    
    # F1 Score
    bars3 = axes[2].bar(all_models, f1_scores, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
    axes[2].set_ylabel('F1 Score', fontsize=12, fontweight='bold')
    axes[2].set_title('F1 Score Comparison', fontsize=14, fontweight='bold')
    axes[2].set_ylim([0, 1])
    axes[2].grid(axis='y', alpha=0.3)
    axes[2].tick_params(axis='x', rotation=45)
    for bar, val in zip(bars3, f1_scores):
        axes[2].text(bar.get_x() + bar.get_width()/2., val + 0.02,
                    f'{val:.3f}', ha='center', fontweight='bold', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'performance_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Performance comparison chart saved")


def create_performance_table(ensemble_avg, individual_avg, save_dir):
    """Create a detailed performance table."""
    
    # Prepare data
    rows = []
    rows.append(['Model', 'Dice', 'IoU', 'Accuracy', 'Precision', 'Recall', 'F1'])
    rows.append(['─' * 15] * 7)
    
    # Ensemble
    rows.append([
        '★ ENSEMBLE',
        f"{ensemble_avg['dice']:.4f}",
        f"{ensemble_avg['iou']:.4f}",
        f"{ensemble_avg['accuracy']:.4f}",
        f"{ensemble_avg['precision']:.4f}",
        f"{ensemble_avg['recall']:.4f}",
        f"{ensemble_avg['f1']:.4f}"
    ])
    
    rows.append(['─' * 15] * 7)
    
    # Individual models
    for name, metrics in individual_avg.items():
        rows.append([
            name,
            f"{metrics['dice']:.4f}",
            f"{metrics['iou']:.4f}",
            f"{metrics['accuracy']:.4f}",
            f"{metrics['precision']:.4f}",
            f"{metrics['recall']:.4f}",
            f"{metrics['f1']:.4f}"
        ])
    
    # Calculate improvement
    rows.append(['─' * 15] * 7)
    avg_individual_dice = np.mean([individual_avg[name]['dice'] for name in individual_avg.keys()])
    improvement = ((ensemble_avg['dice'] - avg_individual_dice) / avg_individual_dice) * 100
    rows.append([
        'Improvement',
        f"+{improvement:.2f}%",
        '', '', '', '', ''
    ])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')
    
    table = ax.table(cellText=rows, cellLoc='center', loc='center',
                    colWidths=[0.2, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)
    
    # Style header
    for i in range(7):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style ensemble row
    for i in range(7):
        table[(2, i)].set_facecolor('#e74c3c')
        table[(2, i)].set_text_props(weight='bold', color='white')
    
    # Style improvement row
    for i in range(7):
        table[(len(rows)-1, i)].set_facecolor('#2ecc71')
        table[(len(rows)-1, i)].set_text_props(weight='bold', color='white')
    
    plt.title('Ensemble vs Individual Models - Performance Metrics', 
             fontsize=16, fontweight='bold', pad=20)
    plt.savefig(os.path.join(save_dir, 'performance_table.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Performance table saved")


# ========== VISUALIZATION ==========

def visualize_ensemble_uncertainty(results, save_dir, num_samples=10):
    """Visualize ensemble uncertainty at ENSEMBLE PREDICTED boundary."""
    os.makedirs(save_dir, exist_ok=True)
    
    sample_count = 0
    for batch_idx in range(len(results['predictions'])):
        if sample_count >= num_samples:
            break
            
        batch_preds = results['predictions'][batch_idx]
        batch_uncerts = results['uncertainties'][batch_idx]
        batch_masks = results['masks'][batch_idx]
        batch_images = results['images'][batch_idx]
        
        for i in range(batch_preds.size(0)):
            if sample_count >= num_samples:
                break
            
            img = batch_images[i, 0].numpy()
            mask_gt = batch_masks[i, 0].numpy()
            pred_mean = batch_preds[i, 0].numpy()
            pred_var = batch_uncerts[i, 0].numpy()
            pred_binary = (pred_mean > 0.5).astype(np.float32)
            
            # ✅ Extract ENSEMBLE PREDICTED boundary
            kernel = np.ones((5, 5), np.uint8)
            boundary_pred = cv2.dilate(pred_binary, kernel, iterations=1) - cv2.erode(pred_binary, kernel, iterations=1)
            
            # Normalize uncertainty
            unc_norm = (pred_var - pred_var.min()) / (pred_var.max() - pred_var.min() + 1e-8)
            
            # Boundary uncertainty
            boundary_unc = np.full_like(unc_norm, np.nan)
            boundary_unc[boundary_pred > 0] = unc_norm[boundary_pred > 0]
            
            # Visualize
            fig, axes = plt.subplots(2, 2, figsize=(12, 12))
            
            axes[0, 0].imshow(img, cmap='gray')
            axes[0, 0].set_title('Input Image', fontsize=12, fontweight='bold')
            axes[0, 0].axis('off')
            
            axes[0, 1].imshow(img, cmap='gray')
            axes[0, 1].contour(mask_gt, colors='green', linewidths=3)
            axes[0, 1].set_title('Ground Truth', fontsize=12, fontweight='bold')
            axes[0, 1].axis('off')
            
            axes[1, 0].imshow(img, cmap='gray')
            axes[1, 0].contour(pred_binary, colors='blue', linewidths=3)
            axes[1, 0].set_title(f'Ensemble Prediction\n({len(results["individual_predictions"])} Models)', fontsize=12, fontweight='bold')
            axes[1, 0].axis('off')
            
            # ✅ ENSEMBLE BOUNDARY UNCERTAINTY
            axes[1, 1].imshow(img, cmap='gray')
            cmap = mcolors.LinearSegmentedColormap.from_list('conf', ['green', 'yellow', 'red'], N=100)
            im = axes[1, 1].imshow(boundary_unc, cmap=cmap, alpha=0.85, vmin=0, vmax=1)
            axes[1, 1].set_title('⭐ ENSEMBLE BOUNDARY\nUNCERTAINTY ⭐', fontsize=12, fontweight='bold')
            axes[1, 1].axis('off')
            plt.colorbar(im, ax=axes[1, 1], fraction=0.046)
            
            dice = 2*np.sum(pred_binary*mask_gt)/(np.sum(pred_binary)+np.sum(mask_gt)+1e-8)
            avg_unc = np.nanmean(boundary_unc)
            
            fig.suptitle(f'Sample {sample_count+1} | Ensemble Dice: {dice:.4f} | Avg Boundary Uncertainty: {avg_unc:.4f}',
                        fontsize=13, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, f'sample_{sample_count+1}.png'), dpi=200, bbox_inches='tight')
            plt.close()
            sample_count += 1
    
    print(f"✓ Saved {sample_count} ensemble uncertainty visualizations")


def visualize_individual_models(results, save_dir, num_samples=5):
    """Show predictions from each individual model."""
    individual_dir = os.path.join(save_dir, "individual_models")
    os.makedirs(individual_dir, exist_ok=True)
    
    model_names = list(results['individual_predictions'].keys())
    num_models = len(model_names)
    
    sample_count = 0
    for batch_idx in range(len(results['predictions'])):
        if sample_count >= num_samples:
            break
        
        batch_images = results['images'][batch_idx]
        batch_masks = results['masks'][batch_idx]
        
        for i in range(batch_images.size(0)):
            if sample_count >= num_samples:
                break
            
            img = batch_images[i, 0].numpy()
            mask_gt = batch_masks[i, 0].numpy()
            
            # Create grid: 2 rows, 3 columns (GT + 5 models = 6 panels)
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.flatten()
            
            # Ground truth
            axes[0].imshow(img, cmap='gray')
            axes[0].contour(mask_gt, colors='green', linewidths=3)
            axes[0].set_title('Ground Truth', fontsize=12, fontweight='bold')
            axes[0].axis('off')
            
            # Individual model predictions
            for idx, name in enumerate(model_names):
                pred = results['individual_predictions'][name][batch_idx][i, 0].numpy()
                pred_binary = (pred > 0.5).astype(np.float32)
                
                axes[idx + 1].imshow(img, cmap='gray')
                axes[idx + 1].contour(pred_binary, colors='blue', linewidths=2)
                
                dice = 2*np.sum(pred_binary*mask_gt)/(np.sum(pred_binary)+np.sum(mask_gt)+1e-8)
                axes[idx + 1].set_title(f'{name}\nDice: {dice:.4f}', fontsize=11, fontweight='bold')
                axes[idx + 1].axis('off')
            
            fig.suptitle(f'Sample {sample_count+1} - Individual Model Predictions', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(os.path.join(individual_dir, f'sample_{sample_count+1}_all_models.png'), 
                       dpi=200, bbox_inches='tight')
            plt.close()
            sample_count += 1
    
    print(f"✓ Saved {sample_count} individual model comparison visualizations")


# ========== MAIN ==========

def main():
    print("=" * 70)
    print("ENSEMBLE UNCERTAINTY - 5 MODELS")
    print("=" * 70)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load all 5 models
    models = load_all_models(device)
    
    if len(models) == 0:
        print("\n❌ ERROR: No models loaded!")
        print("\nPlease check:")
        print("1. Checkpoint files exist at the specified paths")
        print("2. Model architectures match your trained models")
        print("\nCurrent MODEL_PATHS:")
        for name, path in MODEL_PATHS.items():
            exists = "✓" if os.path.exists(path) else "✗"
            print(f"  {exists} {name}: {path}")
        return
    
    # Load test data
    print("\nLoading test data...")
    test_x, test_y = load_test_data()
    print(f"✓ Test samples: {len(test_x)}")
    
    test_dataset = BUSBRADataset(test_x, test_y, IMAGE_SIZE)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)
    
    # Compute ensemble uncertainty
    results = compute_ensemble_uncertainty(models, test_loader, device)
    
    # ✅ COMPUTE PERFORMANCE METRICS
    ensemble_avg, individual_avg = compute_ensemble_metrics(results)
    
    # ✅ CREATE PERFORMANCE VISUALIZATIONS
    plot_performance_comparison(ensemble_avg, individual_avg, OUTPUT_DIR)
    create_performance_table(ensemble_avg, individual_avg, OUTPUT_DIR)
    
    # Visualize uncertainty
    visualize_ensemble_uncertainty(results, OUTPUT_DIR, num_samples=10)
    visualize_individual_models(results, OUTPUT_DIR, num_samples=5)
    
    print("\n" + "=" * 70)
    print("✅ ENSEMBLE UNCERTAINTY COMPLETE!")
    print("=" * 70)
    print(f"  Results: {OUTPUT_DIR}")
    print(f"  - Ensemble uncertainty visualizations: 10 samples")
    print(f"  - Individual model comparisons: 5 samples")
    print(f"  - Performance comparison chart")
    print(f"  - Performance metrics table")
    print("=" * 70)


if __name__ == "__main__":
    main()