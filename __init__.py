# ==============================
# Imports
# ==============================

# --- S3 Nodes ---
from .s3_image_node import (
    NODE_CLASS_MAPPINGS as S3_IMAGE_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as S3_IMAGE_NAMES,
)
from .s3_video_node import (
    NODE_CLASS_MAPPINGS as S3_VIDEO_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as S3_VIDEO_NAMES,
)

# --- Azure Nodes ---
from .azure_image_node import (
    NODE_CLASS_MAPPINGS as AZURE_IMAGE_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as AZURE_IMAGE_NAMES,
)
from .azure_video_node import (
    NODE_CLASS_MAPPINGS as AZURE_VIDEO_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as AZURE_VIDEO_NAMES,
)

# --- Latent Nodes ---
from .latent_save_output_node import (
    NODE_CLASS_MAPPINGS as LATENT_SAVE_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as LATENT_SAVE_NAMES,
)
from .latent_load_node import (
    NODE_CLASS_MAPPINGS as LATENT_LOAD_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as LATENT_LOAD_NAMES,
)

# --- Conditioning JSON Nodes ---
from .conditioning_load_json_node import (
    NODE_CLASS_MAPPINGS as COND_LOAD_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as COND_LOAD_NAMES,
)
from .conditioning_save_json_node import (
    NODE_CLASS_MAPPINGS as COND_SAVE_CLASSES,
    NODE_DISPLAY_NAME_MAPPINGS as COND_SAVE_NAMES,
)


# ==============================
# Registry Assembly
# ==============================

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

NODE_GROUPS = [
    (S3_IMAGE_CLASSES, S3_IMAGE_NAMES),
    (S3_VIDEO_CLASSES, S3_VIDEO_NAMES),
    (AZURE_IMAGE_CLASSES, AZURE_IMAGE_NAMES),
    (AZURE_VIDEO_CLASSES, AZURE_VIDEO_NAMES),
    (LATENT_SAVE_CLASSES, LATENT_SAVE_NAMES),
    (LATENT_LOAD_CLASSES, LATENT_LOAD_NAMES),
    (COND_LOAD_CLASSES, COND_LOAD_NAMES),
    (COND_SAVE_CLASSES, COND_SAVE_NAMES),
]

for class_map, name_map in NODE_GROUPS:
    NODE_CLASS_MAPPINGS.update(class_map)
    NODE_DISPLAY_NAME_MAPPINGS.update(name_map)
