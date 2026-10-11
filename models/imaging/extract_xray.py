import os
import zipfile

zip_path = r"C:\Users\vaibh\Downloads\x-ray.zip"
target_dir = r"C:\AI_HMS\models\imaging\data\chest_xray"

os.makedirs(target_dir, exist_ok=True)

print(f"Extracting {zip_path} to {target_dir}...")

with zipfile.ZipFile(zip_path, "r") as z:
    for member in z.infolist():
        # Skip MACOSX and hidden files
        if "__MACOSX" in member.filename or ".DS_Store" in member.filename:
            continue
        
        # We want to extract files inside 'chest_xray/chest_xray/' or 'chest_xray/' into train/val/test
        # Normalized relative path
        filename = member.filename.replace("\\", "/")
        parts = filename.split("/")
        
        # Look for 'train', 'val', or 'test'
        target_split = None
        for split_name in ["train", "val", "test"]:
            if split_name in parts:
                idx = parts.index(split_name)
                # Ensure it has class name after split (NORMAL or PNEUMONIA)
                if len(parts) > idx + 1 and parts[idx + 1] in ["NORMAL", "PNEUMONIA"]:
                    target_split = "/".join(parts[idx:])
                    break
        
        if target_split and not member.is_dir():
            dest_path = os.path.join(target_dir, os.path.normpath(target_split))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            if not os.path.exists(dest_path):
                with z.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())

print("Extraction complete! Verifying directories...")
for split in ["train", "val", "test"]:
    for cls in ["NORMAL", "PNEUMONIA"]:
        p = os.path.join(target_dir, split, cls)
        count = len(os.listdir(p)) if os.path.exists(p) else 0
        print(f"  {split}/{cls}: {count} images")
