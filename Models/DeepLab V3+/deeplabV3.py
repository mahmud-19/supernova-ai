"""
DeepLab V3+ Training Script
Architecture: DeepLabV3+ with ResNet-50 encoder (segmentation_models_pytorch)
Parameters matched to MobileNetV2 efficiencyNet training setup
"""

import os
import time
import json
import numpy as np
import pandas as pd
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
import albumentations as A
import segmentation_models_pytorch as smp
from tqdm import tqdm


# =============================================================================
# CONFIGURATION  (matched to MobileNetV2 efficiencyNet parameters)
# =============================================================================

BASE_DIR  = "/srv/course/supernova/s202312054/project_file "  # trailing space is part of folder name
IMG_DIR   = os.path.join(BASE_DIR, "image")
MASK_DIR  = os.path.join(BASE_DIR, "musk")
CSV_PATH  = os.path.join(BASE_DIR, "bus_data.csv")

CHECKPOINT_DIR = "/srv/course/supernova/s202312054/DeepLab V3+/checkpoints"

# Model
ENCODER_NAME   = 'resnet50'       # DeepLabV3+ encoder
ENCODER_WEIGHTS = 'imagenet'

# Training  (same as MobileNetV2 notebook)
IMAGE_SIZE    = (256, 256)
BATCH_SIZE    = 8
NUM_EPOCHS    = 500
LEARNING_RATE = 1e-4
MIN_LR        = 1e-6

# Data split  (same as MobileNetV2 notebook)
TRAIN_RATIO  = 0.75
VAL_RATIO    = 0.15
TEST_RATIO   = 0.10
RANDOM_SEED  = 42


# =============================================================================
# DATASET
# =============================================================================

class BUSBRADataset(Dataset):
    def __init__(self, images_path, masks_path, size=(256, 256), transform=None):
        self.images_path = images_path
        self.masks_path  = masks_path
        self.size        = size
        self.transform   = transform

    def __len__(self):
        return len(self.images_path)

    def __getitem__(self, index):
        image = cv2.imread(self.images_path[index], cv2.IMREAD_GRAYSCALE)
        mask  = cv2.imread(self.masks_path[index],  cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise FileNotFoundError(f"Image not found: {self.images_path[index]}")
        if mask is None:
            raise FileNotFoundError(f"Mask not found: {self.masks_path[index]}")

        if self.transform is not None:
            augmented = self.transform(image=image, mask=mask)
            image = augmented["image"]
            mask  = augmented["mask"]

        image = cv2.resize(image, self.size)
        mask  = cv2.resize(mask,  self.size, interpolation=cv2.INTER_NEAREST)

        image = image.astype(np.float32) / 255.0
        mask  = (mask > 127).astype(np.float32)

        image = np.expand_dims(image, axis=0)
        mask  = np.expand_dims(mask,  axis=0)

        return torch.from_numpy(image), torch.from_numpy(mask)


def load_data(csv_path, img_dir, mask_dir):
    print(f"\nChecking paths:")
    print(f"  CSV:    {csv_path}  -> exists: {os.path.exists(csv_path)}")
    print(f"  Images: {img_dir}  -> exists: {os.path.exists(img_dir)}")
    print(f"  Masks:  {mask_dir}  -> exists: {os.path.exists(mask_dir)}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if not os.path.exists(img_dir):
        raise FileNotFoundError(f"Image dir not found: {img_dir}")
    if not os.path.exists(mask_dir):
        raise FileNotFoundError(f"Mask dir not found: {mask_dir}")

    df = pd.read_csv(csv_path)
    print(f"CSV loaded: {len(df)} entries")

    unique_cases = df["Case"].unique()
    train_cases, temp_cases = train_test_split(
        unique_cases, test_size=(VAL_RATIO + TEST_RATIO), random_state=RANDOM_SEED
    )
    val_cases, test_cases = train_test_split(
        temp_cases, test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO), random_state=RANDOM_SEED
    )

    def get_paths(subset_df):
        img_paths, mask_paths = [], []
        missing = 0
        for _, row in subset_df.iterrows():
            img_id = row["ID"]
            img_path = next(
                (os.path.join(img_dir, img_id + ext)
                 for ext in ['.png', '.jpg', '.jpeg']
                 if os.path.exists(os.path.join(img_dir, img_id + ext))),
                None
            )
            mask_id   = img_id.replace("bus_", "mask_")
            mask_path = next(
                (os.path.join(mask_dir, mask_id + ext)
                 for ext in ['.png', '.jpg', '.jpeg']
                 if os.path.exists(os.path.join(mask_dir, mask_id + ext))),
                None
            )
            if img_path and mask_path:
                img_paths.append(img_path)
                mask_paths.append(mask_path)
            else:
                missing += 1
                if missing <= 3:
                    print(f"  Missing: {img_id}")
        if missing:
            print(f"  Total missing: {missing}")
        return img_paths, mask_paths

    print("\nLoading splits...")
    train_x, train_y = get_paths(df[df["Case"].isin(train_cases)])
    val_x,   val_y   = get_paths(df[df["Case"].isin(val_cases)])
    test_x,  test_y  = get_paths(df[df["Case"].isin(test_cases)])

    return (train_x, train_y), (val_x, val_y), (test_x, test_y)


# =============================================================================
# LOSS & METRICS  (same as MobileNetV2 notebook)
# =============================================================================

class DiceLoss(nn.Module):
    def forward(self, pred, target):
        pred   = torch.sigmoid(pred).view(-1)
        target = target.view(-1)
        intersection = (pred * target).sum()
        return 1 - (2. * intersection + 1e-5) / (pred.sum() + target.sum() + 1e-5)


class DiceBCELoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.dice = DiceLoss()
        self.bce  = nn.BCEWithLogitsLoss()

    def forward(self, pred, target):
        return 0.5 * self.dice(pred, target) + 0.5 * self.bce(pred, target)


def dice_coefficient(pred, target):
    pred   = (torch.sigmoid(pred) > 0.5).float().view(-1)
    target = target.view(-1)
    return ((2. * (pred * target).sum() + 1e-5) / (pred.sum() + target.sum() + 1e-5)).item()


def iou_score(pred, target):
    pred   = (torch.sigmoid(pred) > 0.5).float().view(-1)
    target = target.view(-1)
    intersection = (pred * target).sum()
    return ((intersection + 1e-5) / (pred.sum() + target.sum() - intersection + 1e-5)).item()


# =============================================================================
# TRAINING LOOPS  (same as MobileNetV2 notebook, with mixed precision)
# =============================================================================

def train_epoch(model, loader, optimizer, loss_fn, device, scaler=None):
    model.train()
    epoch_loss = epoch_dice = 0.0
    pbar = tqdm(loader, desc='Training')
    for images, masks in pbar:
        images = images.to(device, non_blocking=True)
        masks  = masks.to(device,  non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.amp.autocast('cuda'):
                outputs = model(images)
                loss    = loss_fn(outputs, masks)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss    = loss_fn(outputs, masks)
            loss.backward()
            optimizer.step()
        dice = dice_coefficient(outputs, masks)
        epoch_loss += loss.item()
        epoch_dice += dice
        pbar.set_postfix({'loss': f'{loss.item():.4f}', 'dice': f'{dice:.4f}'})
    return epoch_loss / len(loader), epoch_dice / len(loader)


def validate_epoch(model, loader, loss_fn, device, scaler=None):
    model.eval()
    epoch_loss = epoch_dice = epoch_iou = 0.0
    pbar = tqdm(loader, desc='Validation')
    with torch.no_grad():
        for images, masks in pbar:
            images = images.to(device, non_blocking=True)
            masks  = masks.to(device,  non_blocking=True)
            if scaler is not None:
                with torch.amp.autocast('cuda'):
                    outputs = model(images)
                    loss    = loss_fn(outputs, masks)
            else:
                outputs = model(images)
                loss    = loss_fn(outputs, masks)
            dice = dice_coefficient(outputs, masks)
            iou  = iou_score(outputs, masks)
            epoch_loss += loss.item()
            epoch_dice += dice
            epoch_iou  += iou
            pbar.set_postfix({'loss': f'{loss.item():.4f}', 'dice': f'{dice:.4f}'})
    n = len(loader)
    return epoch_loss / n, epoch_dice / n, epoch_iou / n


# =============================================================================
# TEST SET EVALUATION
# =============================================================================

def evaluate_test_set(model, test_x, test_y, device):
    """Load best_model.pth and compute pixel-level metrics on the test set."""
    best_model_path = os.path.join(CHECKPOINT_DIR, 'best_model.pth')
    if not os.path.exists(best_model_path):
        print("best_model.pth not found — skipping test evaluation.")
        return

    checkpoint = torch.load(best_model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    test_dataset = BUSBRADataset(test_x, test_y, IMAGE_SIZE, None)
    test_loader  = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=2, pin_memory=torch.cuda.is_available())

    TP = TN = FP = FN = 0

    print("\nTesting Model on Independent Test Set...")
    with torch.no_grad():
        for images, masks in tqdm(test_loader, desc='Testing'):
            images = images.to(device, non_blocking=True)
            masks  = masks.to(device,  non_blocking=True)
            with torch.amp.autocast('cuda') if torch.cuda.is_available() else torch.inference_mode():
                outputs = model(images)
            preds  = (torch.sigmoid(outputs) > 0.5).float()
            target = masks

            TP += (preds * target).sum().item()
            TN += ((1 - preds) * (1 - target)).sum().item()
            FP += (preds * (1 - target)).sum().item()
            FN += ((1 - preds) * target).sum().item()

    accuracy  = (TP + TN) / (TP + TN + FP + FN + 1e-8)
    precision = TP / (TP + FP + 1e-8)
    recall    = TP / (TP + FN + 1e-8)
    f1        = 2 * precision * recall / (precision + recall + 1e-8)
    iou       = TP / (TP + FP + FN + 1e-8)

    print("=" * 30)
    print("  FINAL EVALUATION METRICS")
    print("=" * 30)
    print(f"Accuracy:         {accuracy:.4f}")
    print(f"Precision:        {precision:.4f}")
    print(f"Recall:           {recall:.4f}")
    print(f"F1 Score (Dice):  {f1:.4f}")
    print(f"IoU Score:        {iou:.4f}")
    print("=" * 30)

    return {
        'accuracy': accuracy, 'precision': precision,
        'recall': recall, 'f1_dice': f1, 'iou': iou
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "=" * 60)
    print("DeepLab V3+ TRAINING - 500 EPOCHS")
    print(f"Encoder: {ENCODER_NAME}")
    print("=" * 60)

    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(RANDOM_SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark     = True

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print(f"\nCheckpoints: {CHECKPOINT_DIR}")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        use_amp   = True
        num_workers = 4
        batch_size  = BATCH_SIZE
    else:
        use_amp     = False
        num_workers = 2
        batch_size  = max(4, BATCH_SIZE // 4)

    scaler = torch.amp.GradScaler('cuda') if use_amp else None

    # Data
    print("\n" + "=" * 60)
    print("LOADING DATA")
    print("=" * 60)
    try:
        (train_x, train_y), (val_x, val_y), (test_x, test_y) = load_data(CSV_PATH, IMG_DIR, MASK_DIR)
    except Exception as e:
        print(f"\nERROR: {e}")
        return

    print(f"\nTrain={len(train_x)}  Val={len(val_x)}  Test={len(test_x)}")
    if len(train_x) == 0:
        print("ERROR: No training samples found.")
        return

    # Augmentation  (same as MobileNetV2 notebook)
    train_transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.RandomRotate90(p=0.3),
        A.Affine(shift_limit=0.05, scale_limit=0.1, rotate_limit=15, p=0.5),
        A.ElasticTransform(alpha=1, sigma=50, p=0.2),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
        A.GaussNoise(p=0.2),
    ])

    train_dataset = BUSBRADataset(train_x, train_y, IMAGE_SIZE, train_transform)
    val_dataset   = BUSBRADataset(val_x,   val_y,   IMAGE_SIZE, None)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                              num_workers=num_workers, pin_memory=torch.cuda.is_available())
    val_loader   = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False,
                              num_workers=num_workers, pin_memory=torch.cuda.is_available())

    # Model — DeepLabV3+
    print("\n" + "=" * 60)
    print("BUILDING MODEL")
    print("=" * 60)
    model = smp.DeepLabV3Plus(
        encoder_name    = ENCODER_NAME,
        encoder_weights = ENCODER_WEIGHTS,
        in_channels     = 1,
        classes         = 1,
        activation      = None
    ).to(device)

    total_params     = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model: DeepLabV3+ + {ENCODER_NAME}")
    print(f"Params: {total_params:,}  |  Trainable: {trainable_params:,}")
    print(f"Image size: {IMAGE_SIZE}  |  Batch: {batch_size}  |  Mixed precision: {use_amp}")

    loss_fn   = DiceBCELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=20, min_lr=MIN_LR
    )

    best_val_dice = 0.0
    best_epoch    = 0
    history       = []

    print("\n" + "=" * 60)
    print(f"STARTING TRAINING  |  {NUM_EPOCHS} epochs  |  device: {device}")
    print("=" * 60)

    start_training_time = time.time()

    for epoch in range(1, NUM_EPOCHS + 1):
        start_time = time.time()

        train_loss, train_dice = train_epoch(model, train_loader, optimizer, loss_fn, device, scaler)
        val_loss,   val_dice,  val_iou = validate_epoch(model, val_loader, loss_fn, device, scaler)

        elapsed = time.time() - start_time
        print(f"\nEpoch [{epoch:03d}/{NUM_EPOCHS}] {int(elapsed//60)}m {int(elapsed%60)}s")
        print(f"  Train  Loss: {train_loss:.4f}  Dice: {train_dice:.4f}")
        print(f"  Val    Loss: {val_loss:.4f}  Dice: {val_dice:.4f}  IoU: {val_iou:.4f}")

        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]['lr']
        print(f"  LR: {current_lr:.2e}")

        if val_dice > best_val_dice:
            best_val_dice = val_dice
            best_epoch    = epoch
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'val_dice': val_dice,
                'val_iou':  val_iou,
            }, os.path.join(CHECKPOINT_DIR, 'best_model.pth'))
            print(f"  New best Val Dice: {val_dice:.4f} - saved!")

        history.append({
            'epoch': epoch, 'train_loss': train_loss, 'train_dice': train_dice,
            'val_loss': val_loss, 'val_dice': val_dice, 'val_iou': val_iou,
            'learning_rate': current_lr
        })

        if epoch % 50 == 0:
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
            }, os.path.join(CHECKPOINT_DIR, f'model_epoch_{epoch}.pth'))
            print(f"  Checkpoint saved: model_epoch_{epoch}.pth")

        if epoch == 10:
            avg_t     = (time.time() - start_training_time) / epoch
            remaining = avg_t * (NUM_EPOCHS - epoch)
            print(f"  Estimated remaining: {int(remaining//3600)}h {int((remaining%3600)//60)}m")

    # Save final
    torch.save({
        'epoch': NUM_EPOCHS,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
    }, os.path.join(CHECKPOINT_DIR, 'final_model.pth'))

    total_time = time.time() - start_training_time
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Total time:     {int(total_time//3600)}h {int((total_time%3600)//60)}m")
    print(f"Best Val Dice:  {best_val_dice:.4f} at epoch {best_epoch}")
    print(f"Final Val Dice: {history[-1]['val_dice']:.4f}  IoU: {history[-1]['val_iou']:.4f}")

    with open(os.path.join(CHECKPOINT_DIR, 'training_history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    summary = {
        'model': 'DeepLabV3+', 'encoder': ENCODER_NAME,
        'total_epochs': NUM_EPOCHS, 'best_val_dice': float(best_val_dice),
        'best_epoch': int(best_epoch),
        'final_val_dice': float(history[-1]['val_dice']),
        'final_val_iou':  float(history[-1]['val_iou']),
        'train_samples': len(train_x), 'val_samples': len(val_x), 'test_samples': len(test_x),
        'image_size': IMAGE_SIZE, 'batch_size': batch_size,
        'device': str(device), 'training_time_hours': round(total_time / 3600, 2)
    }
    with open(os.path.join(CHECKPOINT_DIR, 'training_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nAll files saved to: {CHECKPOINT_DIR}")
    print("=" * 60)

    # Final evaluation on the independent test set
    test_metrics = evaluate_test_set(model, test_x, test_y, device)
    if test_metrics:
        with open(os.path.join(CHECKPOINT_DIR, 'test_metrics.json'), 'w') as f:
            json.dump(test_metrics, f, indent=2)


if __name__ == "__main__":
    main()
