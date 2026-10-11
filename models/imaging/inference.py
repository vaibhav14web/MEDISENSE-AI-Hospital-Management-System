"""
Inference Engine for Chest X-Ray Pneumonia Classifier.
Provides single-image and batch prediction, clinical triage categorization,
and Grad-CAM heatmap generation.
"""

import os
import io
import time
import base64
import torch
from PIL import Image
from torchvision import transforms

# Ensure current module path
current_dir = os.path.dirname(os.path.abspath(__file__))
import sys
if current_dir not in sys.path:
    sys.path.append(current_dir)

from model import ChestXRayClassifier
from gradcam import GradCAM

class ChestXRayInferenceEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ChestXRayInferenceEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, checkpoint_path=None, device=None):
        if getattr(self, "_initialized", False):
            return

        if checkpoint_path is None:
            checkpoint_path = os.path.join(r"C:\AI_HMS\models\artifacts", "chest_xray_model.pt")

        self.checkpoint_path = checkpoint_path
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self.model = None
        self.gradcam = None
        self.class_names = ["NORMAL", "PNEUMONIA"]

        if os.path.exists(self.checkpoint_path):
            self.load_model()
        else:
            print(f"Warning: Checkpoint not found at {self.checkpoint_path}. Engine will initialize once trained.")

        self._initialized = True

    def load_model(self):
        print(f"Loading Chest X-Ray model from {self.checkpoint_path} onto {self.device}...")
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        backbone = checkpoint.get("backbone", "resnet18")
        self.class_names = checkpoint.get("class_names", ["NORMAL", "PNEUMONIA"])

        self.model = ChestXRayClassifier(backbone=backbone, pretrained=False, num_classes=2)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.gradcam = GradCAM(self.model)
        print("Chest X-Ray model and Grad-CAM successfully loaded!")

    def predict(self, image_input, include_heatmap=True):
        """
        image_input: file path (str), file-like object / bytes, or PIL Image.
        returns: dict with predictions, probabilities, clinical findings, and optional heatmap base64.
        """
        start_time = time.time()

        if self.model is None:
            if os.path.exists(self.checkpoint_path):
                self.load_model()
            else:
                raise RuntimeError(f"Model checkpoint not found at {self.checkpoint_path}. Train the model first.")

        # Load image into PIL RGB
        if isinstance(image_input, str):
            orig_pil = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, (bytes, bytearray)):
            orig_pil = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif hasattr(image_input, "read"):
            orig_pil = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            orig_pil = image_input.convert("RGB")
        else:
            raise ValueError("Unsupported image input format.")

        # Transform for model
        input_tensor = self.transform(orig_pil).unsqueeze(0).to(self.device)

        # Forward pass
        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()

        prob_normal = float(probs[0])
        prob_pneumonia = float(probs[1])

        pred_idx = 1 if prob_pneumonia >= 0.5 else 0
        predicted_class = self.class_names[pred_idx]
        confidence = float(probs[pred_idx])

        # Clinical Triage & Findings
        if predicted_class == "PNEUMONIA":
            acuity = "URGENT_TRIAGE"
            if prob_pneumonia > 0.85:
                findings = "High-confidence pulmonary consolidation/infiltrate detected. Recommend immediate clinician review and antibiotic/supportive therapy evaluation."
            else:
                findings = "Equivocal or moderate opacities detected consistent with early or viral pneumonia. Recommend clinical correlation with patient auscultation and SpO2."
        else:
            acuity = "ROUTINE"
            if prob_normal > 0.85:
                findings = "Clear lung fields with no focal consolidation or acute cardiopulmonary abnormalities detected."
            else:
                findings = "Predominantly clear lung fields; minimal non-specific markings. Low risk for acute pneumonia."

        # Grad-CAM heatmap generation
        heatmap_base64 = None
        if include_heatmap and self.gradcam is not None:
            # Generate heatmap for the predicted or pneumonia class
            heatmap = self.gradcam.generate_heatmap(input_tensor, target_class=pred_idx)
            blended_img = self.gradcam.overlay_on_image(orig_pil, heatmap, alpha=0.45)
            
            buffered = io.BytesIO()
            blended_img.save(buffered, format="JPEG", quality=90)
            heatmap_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "predicted_class": predicted_class,
            "confidence": round(confidence, 4),
            "probability_pneumonia": round(prob_pneumonia, 4),
            "probability_normal": round(prob_normal, 4),
            "acuity_level": acuity,
            "clinical_findings": findings,
            "latency_ms": latency_ms,
            "gradcam_heatmap_base64": heatmap_base64,
            "image_size": [orig_pil.width, orig_pil.height]
        }

# Global singleton helper
def get_inference_engine():
    return ChestXRayInferenceEngine()
