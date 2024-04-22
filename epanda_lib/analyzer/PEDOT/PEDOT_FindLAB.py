"""For PEDOT films calculates the Delta E00 values between the coloring and bleaching images."""
import os

import numpy as np
from PIL import Image, ImageDraw
from skimage import color
from skimage.color.delta_e import deltaE_ciede2000

from .pedot_classes import RequiredData, RawMetrics


def extract_circular_region(image_path, radius=300, show_region=True) -> np.ndarray:
    """Extracts the average RGB values from a circular region of an image."""
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    center = (width // 2 + 75, height // 2)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).ellipse(
        (
            center[0] - radius,
            center[1] - radius,
            center[0] + radius,
            center[1] + radius,
        ),
        fill=255,
    )
    result = Image.new("RGB", (width, height))
    result.paste(img, mask=mask)
    result_array = np.array(result)
    mask_array = np.array(mask)
    masked_pixels = result_array[mask_array > 0]

    if show_region:
        display_img = img.copy()
        draw = ImageDraw.Draw(display_img)
        draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline="white",
        )
        # Split the path from the extension
        file_path, _ = os.path.splitext(image_path)
        # Save using the modified path
        display_img.save(f"{file_path}_ROI.png")
        # display_img.show()
    return np.mean(masked_pixels, axis=0)


def rgbtolab(inputs: RequiredData) -> RawMetrics:
    """Converts RGB images to LAB color space and calculates Delta E00 values."""
    experiment_id: int = inputs.experiment_id
    images_by_exp_id: dict = {}.setdefault(
        experiment_id, {"deposition": None, "bleaching": None, "coloring": None}
    )
    images_by_exp_id[experiment_id]["deposition"] = inputs.BeforeDeposition
    images_by_exp_id[experiment_id]["bleaching"] = inputs.AfterBleaching
    images_by_exp_id[experiment_id]["coloring"] = inputs.AfterColoring

    lab_values_dict = {}
    white_standard_path = inputs.BeforeDeposition
    white_standard_rgb = extract_circular_region(white_standard_path)
    for image_type in ["bleaching", "coloring"]:
        image_path = images_by_exp_id[experiment_id][image_type]
        if image_path:
            average_rgb = extract_circular_region(image_path)
            original_rgb = np.round(average_rgb).astype(int)

            white_standard_rgb_safe = np.where(
                white_standard_rgb == 0, 1, white_standard_rgb
            )
            corrected_rgb = np.clip(
                (average_rgb / white_standard_rgb_safe) * 255, 0, 255
            ).astype(int)

            lab_values = color.rgb2lab((corrected_rgb / 255).reshape(1, 1, 3)).flatten()

            lab_values_dict[experiment_id] = lab_values_dict.get(experiment_id, {})
            lab_values_dict[experiment_id][image_type] = lab_values
            lab_values_dict[experiment_id][f"{image_type}_original_rgb"] = original_rgb

    metrics: RawMetrics = None
    metrics.experiment_id = experiment_id
    for experiment_id, labs in lab_values_dict.items():
        if "coloring" in labs and "bleaching" in labs:
            metrics.l_c, metrics.a_c, metrics.b_c = labs["coloring"]
            metrics.b_b, metrics.a_b, metrics.b_b = labs["bleaching"]
            metrics.delta_e00 = deltaE_ciede2000(labs["coloring"], labs["bleaching"])
            metrics.r_c_o, metrics.g_c_o, metrics.b_c_o = labs["coloring_original_rgb"]
            metrics.r_b_o, metrics.g_b_o, metrics.b_b_o = labs["bleaching_original_rgb"]

    return metrics
