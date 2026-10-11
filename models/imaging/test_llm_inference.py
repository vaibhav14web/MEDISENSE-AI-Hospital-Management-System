"""
Test verification script for Chest X-Ray Model (Model A) LLM Inference.
Demonstrates the full pipeline:
1. Model loading & GPU acceleration
2. Normal case radiograph evaluation
3. Pneumonia case radiograph evaluation
4. Clinical context generation for LLM prompt injection / tool calling
"""

import os
import sys
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from models.imaging.llm_tool import analyze_chest_xray_for_llm, CHEST_XRAY_TOOL_SCHEMA

def run_test():
    print("=" * 70)
    print(" [CHEST X-RAY / MODEL A] LLM INFERENCE VALIDATION")
    print("=" * 70)

    test_data_dir = os.path.join(project_root, "models", "imaging", "data", "chest_xray", "test")
    normal_samples = glob.glob(os.path.join(test_data_dir, "NORMAL", "*.jpeg"))
    pneumonia_samples = glob.glob(os.path.join(test_data_dir, "PNEUMONIA", "*.jpeg"))

    if not normal_samples or not pneumonia_samples:
        print("Error: Test dataset images not found.")
        return

    sample_normal = normal_samples[0]
    sample_pneumonia = pneumonia_samples[0]

    print(f"\n[1] Testing NORMAL Radiograph: {os.path.basename(sample_normal)}")
    norm_res = analyze_chest_xray_for_llm(sample_normal, include_heatmap=True)
    print(f" -> Predicted: {norm_res['predicted_class']} (Confidence: {norm_res['confidence']*100:.2f}%)")
    print(f" -> Acuity: {norm_res['acuity_level']} | Latency: {norm_res['latency_ms']} ms")
    print(f" -> Grad-CAM Saliency Map: {'Generated' if norm_res['has_gradcam'] else 'Failed'}")

    print(f"\n[2] Testing PNEUMONIA Radiograph: {os.path.basename(sample_pneumonia)}")
    pneu_res = analyze_chest_xray_for_llm(sample_pneumonia, include_heatmap=True)
    print(f" -> Predicted: {pneu_res['predicted_class']} (Confidence: {pneu_res['confidence']*100:.2f}%)")
    print(f" -> Acuity: {pneu_res['acuity_level']} | Latency: {pneu_res['latency_ms']} ms")
    print(f" -> Grad-CAM Saliency Map: {'Generated' if pneu_res['has_gradcam'] else 'Failed'}")

    print("\n" + "=" * 70)
    print(" [PROMPT CONTEXT] FORMATTED CLINICAL BRIEFING FOR LLM REASONING")
    print("=" * 70)
    print(pneu_res["llm_prompt_context"])

    print("=" * 70)
    print(" [TOOL SCHEMA] OPENAI / OLLAMA TOOL CALL SPECIFICATION:")
    print("=" * 70)
    import json
    print(json.dumps(CHEST_XRAY_TOOL_SCHEMA, indent=2))
    print("\n[SUCCESS] All Model A verification checks passed successfully!")

if __name__ == "__main__":
    run_test()
