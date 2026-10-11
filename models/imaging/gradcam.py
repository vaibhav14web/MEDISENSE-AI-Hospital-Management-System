"""
Grad-CAM (Gradient-weighted Class Activation Mapping) for Chest X-Ray Explainability.
Generates diagnostic heatmaps highlighting the lung regions contributing to the prediction.
"""

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image

class GradCAM:
    def __init__(self, model, target_layer=None):
        self.model = model
        self.target_layer = target_layer if target_layer is not None else model.target_conv_layer
        self.gradients = None
        self.activations = None
        
        # Register hooks
        self.hook_layers()

    def hook_layers(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(self, input_tensor, target_class=None):
        """
        input_tensor: (1, C, H, W) normalized tensor
        target_class: index of class (1 for PNEUMONIA)
        returns: (H, W) numpy array normalized to [0, 1]
        """
        self.model.eval()
        self.model.zero_grad()

        output = self.model(input_tensor)
        if target_class is None:
            target_class = torch.argmax(output, dim=1).item()

        score = output[0, target_class]
        score.backward()

        # Global average pooling over gradients
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True) # (1, C, 1, 1)
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True) # (1, 1, H, W)
        cam = F.relu(cam) # ReLU to keep only positive contributions

        cam = cam.squeeze().cpu().detach().numpy()
        if np.max(cam) > 0:
            cam = (cam - np.min(cam)) / (np.max(cam) - np.min(cam))
        else:
            cam = np.zeros_like(cam)

        return cam

    def overlay_on_image(self, original_pil_image, heatmap, alpha=0.4, colormap="jet"):
        """
        Overlays heatmap on original PIL image and returns an RGB PIL Image.
        """
        # Resize heatmap to match image size
        w, h = original_pil_image.size
        heatmap_resized = Image.fromarray((heatmap * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR)
        heatmap_np = np.array(heatmap_resized) / 255.0

        # Simple Jet colormap generation without requiring matplotlib
        # Jet: Blue -> Cyan -> Yellow -> Red
        r = np.clip(1.5 - np.abs(4.0 * heatmap_np - 3.0), 0.0, 1.0)
        g = np.clip(1.5 - np.abs(4.0 * heatmap_np - 2.0), 0.0, 1.0)
        b = np.clip(1.5 - np.abs(4.0 * heatmap_np - 1.0), 0.0, 1.0)
        color_mask = np.stack([r, g, b], axis=-1) * 255.0

        orig_rgb = original_pil_image.convert("RGB")
        orig_np = np.array(orig_rgb, dtype=np.float32)

        # Blend
        blended = (1.0 - alpha) * orig_np + alpha * color_mask
        blended = np.clip(blended, 0, 255).astype(np.uint8)

        return Image.fromarray(blended)
