"""
Dataset loaders and augmentation pipelines for Chest X-Ray Images.
"""

import os
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

def get_transforms(img_size=224):
    train_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_test_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, val_test_transform

def get_dataloaders(data_dir=r"C:\AI_HMS\models\imaging\data\chest_xray", batch_size=32, num_workers=2):
    train_transform, test_transform = get_transforms()

    train_dir = os.path.join(data_dir, "train")
    val_dir = os.path.join(data_dir, "val")
    test_dir = os.path.join(data_dir, "test")

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    test_dataset = datasets.ImageFolder(test_dir, transform=test_transform)
    val_dataset = datasets.ImageFolder(val_dir, transform=test_transform) if os.path.exists(val_dir) else None

    # Calculate class weights for imbalanced loss handling
    # Class 0: NORMAL, Class 1: PNEUMONIA
    targets = train_dataset.targets
    count_0 = targets.count(0)
    count_1 = targets.count(1)
    total = len(targets)
    
    # Inverse frequency weighting: weight_c = total / (num_classes * count_c)
    weight_0 = total / (2.0 * count_0) if count_0 > 0 else 1.0
    weight_1 = total / (2.0 * count_1) if count_1 > 0 else 1.0
    class_weights = torch.tensor([weight_0, weight_1], dtype=torch.float)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers) if val_dataset else None

    return {
        "train_loader": train_loader,
        "val_loader": val_loader,
        "test_loader": test_loader,
        "class_weights": class_weights,
        "class_names": train_dataset.classes, # ['NORMAL', 'PNEUMONIA']
        "class_to_idx": train_dataset.class_to_idx
    }
