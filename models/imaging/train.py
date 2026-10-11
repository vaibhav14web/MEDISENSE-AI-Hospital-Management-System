"""
Training and Evaluation Pipeline for Chest X-Ray Pneumonia Classifier.
Fine-tunes a Deep CNN using Transfer Learning, evaluates clinical diagnostic metrics,
generates metadata, and registers model in PostgreSQL ai.ai_model_versions.
"""

import os
import sys
import time
import json
import uuid
from datetime import datetime, timezone

import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix

# Ensure current directory and backend directory are in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
from model import ChestXRayClassifier
from dataset import get_dataloaders

def train_and_evaluate(epochs=3, batch_size=32, lr=1e-4, backbone="resnet18"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Starting Chest X-Ray Training on {device} ===")
    if device.type == "cuda":
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")

    data_dir = r"C:\AI_HMS\models\imaging\data\chest_xray"
    loaders = get_dataloaders(data_dir=data_dir, batch_size=batch_size, num_workers=0)
    train_loader = loaders["train_loader"]
    test_loader = loaders["test_loader"]
    class_weights = loaders["class_weights"].to(device)

    print(f"Classes: {loaders['class_names']} | Weights: {class_weights.tolist()}")

    model = ChestXRayClassifier(backbone=backbone, pretrained=True, num_classes=2).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    use_amp = (device.type == "cuda")
    scaler = torch.amp.GradScaler('cuda') if use_amp else None

    best_f1 = 0.0
    best_metrics = {}
    artifacts_dir = r"C:\AI_HMS\models\artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)
    model_save_path = os.path.join(artifacts_dir, "chest_xray_model.pt")
    meta_save_path = os.path.join(artifacts_dir, "chest_xray_model_meta.json")

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        epoch_start = time.time()
        for batch_idx, (images, targets) in enumerate(train_loader):
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad()

            if use_amp:
                with torch.amp.autocast('cuda'):
                    outputs = model(images)
                    loss = criterion(outputs, targets)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(images)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

            if (batch_idx + 1) % 40 == 0 or (batch_idx + 1) == len(train_loader):
                batch_acc = 100.0 * correct / total
                print(f"Epoch [{epoch}/{epochs}] Batch [{batch_idx+1}/{len(train_loader)}] Loss: {loss.item():.4f} Acc: {batch_acc:.2f}%")

        scheduler.step()
        epoch_loss = running_loss / total
        epoch_acc = 100.0 * correct / total

        # Evaluation on Test Set
        model.eval()
        test_loss = 0.0
        all_preds = []
        all_targets = []
        all_probs = []

        with torch.no_grad():
            for images, targets in test_loader:
                images, targets = images.to(device), targets.to(device)
                if use_amp:
                    with torch.amp.autocast('cuda'):
                        outputs = model(images)
                        loss = criterion(outputs, targets)
                else:
                    outputs = model(images)
                    loss = criterion(outputs, targets)

                test_loss += loss.item() * images.size(0)
                probs = torch.softmax(outputs, dim=1)[:, 1] # Probability of Pneumonia
                _, predicted = outputs.max(1)

                all_preds.extend(predicted.cpu().numpy())
                all_targets.extend(targets.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())

        test_total = len(all_targets)
        test_acc = sum(p == t for p, t in zip(all_preds, all_targets)) / test_total
        prec = precision_score(all_targets, all_preds, zero_division=0)
        rec = recall_score(all_targets, all_preds, zero_division=0) # Sensitivity for Pneumonia
        f1 = f1_score(all_targets, all_preds, zero_division=0)
        roc_auc = roc_auc_score(all_targets, all_probs)
        cm = confusion_matrix(all_targets, all_preds)
        # TN, FP, FN, TP
        tn, fp, fn, tp = cm.ravel()
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0 # Specificity for Normal

        print(f"\n--- Epoch {epoch} Evaluation (Time: {time.time()-epoch_start:.1f}s) ---")
        print(f"Train Loss: {epoch_loss:.4f} | Train Acc: {epoch_acc:.2f}%")
        print(f"Test Accuracy: {test_acc*100:.2f}% | Sensitivity (Recall): {rec*100:.2f}% | Specificity: {spec*100:.2f}%")
        print(f"Precision: {prec*100:.2f}% | F1 Score: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
        print(f"Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}\n")

        current_metrics = {
            "epoch": epoch,
            "accuracy": round(float(test_acc), 4),
            "sensitivity_recall": round(float(rec), 4),
            "specificity": round(float(spec), 4),
            "precision": round(float(prec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        }

        if f1 > best_f1:
            best_f1 = f1
            best_metrics = current_metrics
            # Save checkpoint
            torch.save({
                "backbone": backbone,
                "state_dict": model.state_dict(),
                "class_names": loaders["class_names"],
                "metrics": best_metrics
            }, model_save_path)
            print(f">> Saved new best model checkpoint to {model_save_path}")

    total_training_time = round(time.time() - start_time, 2)
    print(f"Training completed in {total_training_time}s! Best F1: {best_f1:.4f}")

    # Generate metadata
    metadata = {
        "model_name": "ChestXRayPneumoniaClassifier",
        "model_type": "DeepConvolutionalNeuralNetwork",
        "backbone": backbone,
        "version": f"v1.{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "framework": "PyTorch / Torchvision",
        "task": "pediatric_chest_radiograph_pneumonia_classification",
        "dataset_reference": "Kermany et al. / Guangzhou Chest X-Ray Cohort (5,856 images)",
        "classes": ["NORMAL", "PNEUMONIA"],
        "training_time_seconds": total_training_time,
        "metrics": best_metrics,
        "artifact_path": model_save_path,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    with open(meta_save_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to {meta_save_path}")

    # Register in PostgreSQL database
    register_model_in_db(metadata)

    return metadata

def register_model_in_db(metadata):
    try:
        from app.db.session import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            # Check if active model exists
            existing = conn.execute(text("""
                SELECT count(*) FROM ai.ai_model_versions 
                WHERE model_name = :name
            """), {"name": metadata["model_name"]}).scalar()

            model_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            conn.execute(text("""
                INSERT INTO ai.ai_model_versions (
                    id, model_name, model_type, version, framework, task,
                    dataset_reference, metrics, artifact_uri, parameters, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :mtype, :version, :framework, :task,
                    :dataset, :metrics, :uri, :params, 'active',
                    :created_at, :updated_at
                )
            """), {
                "id": model_id,
                "name": metadata["model_name"],
                "mtype": metadata["model_type"],
                "version": metadata["version"],
                "framework": metadata["framework"],
                "task": metadata["task"],
                "dataset": metadata["dataset_reference"],
                "metrics": json.dumps(metadata["metrics"]),
                "uri": metadata["artifact_path"],
                "params": json.dumps({"backbone": metadata["backbone"], "input_size": 224}),
                "created_at": now,
                "updated_at": now
            })
            conn.commit()
            print(f"Successfully registered {metadata['model_name']} ({metadata['version']}) in ai.ai_model_versions!")
    except Exception as e:
        print(f"Database registration notice: {e}")

if __name__ == "__main__":
    train_and_evaluate(epochs=3, batch_size=32, lr=1e-4, backbone="resnet18")
