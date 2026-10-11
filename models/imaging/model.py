"""
Deep Learning Model Architecture for Chest X-Ray Pneumonia Classification.
Supports Transfer Learning with ResNet-18/50 and DenseNet-121.
"""

import torch
import torch.nn as nn
import torchvision.models as models

class ChestXRayClassifier(nn.Module):
    def __init__(self, backbone="resnet18", pretrained=True, num_classes=2, dropout_rate=0.3):
        super().__init__()
        self.backbone_name = backbone
        self.num_classes = num_classes

        if backbone == "resnet18":
            weights = models.ResNet18_Weights.DEFAULT if pretrained else None
            self.backbone = models.resnet18(weights=weights)
            in_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(in_features, num_classes)
            )
            self.target_conv_layer = self.backbone.layer4[-1].conv2

        elif backbone == "resnet50":
            weights = models.ResNet50_Weights.DEFAULT if pretrained else None
            self.backbone = models.resnet50(weights=weights)
            in_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(in_features, num_classes)
            )
            self.target_conv_layer = self.backbone.layer4[-1].conv3

        elif backbone == "densenet121":
            weights = models.DenseNet121_Weights.DEFAULT if pretrained else None
            self.backbone = models.densenet121(weights=weights)
            in_features = self.backbone.classifier.in_features
            self.backbone.classifier = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(in_features, num_classes)
            )
            self.target_conv_layer = self.backbone.features.denseblock4

        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

    def forward(self, x):
        return self.backbone(x)

    def get_probabilities(self, x):
        with torch.no_grad():
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1)
        return probs
