"""
LLM Diagnostic Tool for Chest X-Ray Model (Model A).
Provides structured tool calling schema and prompt formatting for LLMs 
(such as OpenAI, Ollama, Claude, or local agents) to integrate Chest X-Ray 
radiograph deep-learning predictions into clinical reasoning workflows.
"""

import os
import sys
import json
from typing import Dict, Any, Optional

# Ensure project root in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from models.imaging.inference import get_inference_engine


def analyze_chest_xray_for_llm(image_path: str, include_heatmap: bool = True) -> Dict[str, Any]:
    """
    Executes deep learning inference on a Chest X-Ray radiograph and formats
    the diagnostic results with clinically grounded context for LLM consumption.
    
    Args:
        image_path: Absolute or relative path to the chest radiograph JPEG/PNG.
        include_heatmap: Whether to generate Grad-CAM visual explainability.
        
    Returns:
        Structured dictionary containing:
        - raw_inference: Numeric probabilities, acuity, class, and latency.
        - llm_context: Human-readable clinical briefing formatted for LLM system/user prompts.
        - tool_call_result: Machine-parseable JSON payload for LLM tool calling.
    """
    if not os.path.isabs(image_path):
        image_path = os.path.normpath(os.path.join(project_root, image_path))
        
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Chest X-Ray image not found at: {image_path}")
        
    engine = get_inference_engine()
    res = engine.predict(image_path, include_heatmap=include_heatmap)
    
    predicted_class = res["predicted_class"]
    confidence = res["confidence"]
    prob_pneu = res["probability_pneumonia"]
    prob_norm = res["probability_normal"]
    acuity = res["acuity_level"]
    findings = res["clinical_findings"]
    latency_ms = res["latency_ms"]
    
    # Formulate standardized clinical briefing for LLM prompt augmentation
    clinical_prompt_context = f"""[CLINICAL IMAGING REPORT: CHEST RADIOGRAPH]
Image Source: {os.path.basename(image_path)}
Model Backbone: ResNet-18 (Deep CNN, Kermany Pediatric Cohort)
Diagnostic Classification: {predicted_class}
Confidence Score: {confidence * 100:.2f}%
Class Probabilities:
  - Pneumonia (Consolidation/Infiltrate): {prob_pneu * 100:.2f}%
  - Normal (Clear Lung Fields): {prob_norm * 100:.2f}%
Triage Acuity Level: {acuity}
Automated Findings: {findings}
Grad-CAM Heatmap Generated: {'Yes' if res.get('gradcam_heatmap_base64') else 'No'}
Inference Latency: {latency_ms} ms

[CLINICAL GUIDELINES FOR LLM REASONING]
1. If triage acuity is URGENT_TRIAGE (Pneumonia detected), review potential bacterial vs. viral etiology indicators, recommend oxygenation assessment (SpO2), auscultation correlation, and urgent pediatric/pulmonary review.
2. If triage acuity is ROUTINE (Normal detected), confirm absence of focal opacities while advising standard differential if respiratory symptoms persist.
3. Treat this deep learning model prediction as an AI triage aid, requiring certified physician sign-off.
"""

    return {
        "status": "success",
        "predicted_class": predicted_class,
        "confidence": confidence,
        "probability_pneumonia": prob_pneu,
        "probability_normal": prob_norm,
        "acuity_level": acuity,
        "clinical_findings": findings,
        "latency_ms": latency_ms,
        "has_gradcam": bool(res.get("gradcam_heatmap_base64")),
        "gradcam_heatmap_base64": res.get("gradcam_heatmap_base64"),
        "llm_prompt_context": clinical_prompt_context
    }


# Standard OpenAI / Anthropic / Ollama tool definition schema
CHEST_XRAY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_chest_xray",
        "description": "Performs deep-learning computer vision analysis on a pediatric or adult chest radiograph (X-ray) to detect pneumonia, assess triage acuity, and compute visual Grad-CAM explainability.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "The file path or URI of the chest radiograph image to evaluate."
                },
                "include_heatmap": {
                    "type": "boolean",
                    "description": "Whether to generate a Grad-CAM saliency heatmap.",
                    "default": True
                }
            },
            "required": ["image_path"]
        }
    }
}
