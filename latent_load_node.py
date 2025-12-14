import os
import hashlib
import safetensors.torch
import folder_paths
import torch
from typing import List

LATENT_EXT = ".latent"
DEFAULT_LATENT_SHAPE = (1, 4, 8, 8)
SD_VAE_SCALE = 0.18215


class LoadLatent:
    """
    Load latent tensors from ComfyUI output directory.
    """

    _cached_latents: List[str] = []
    _cached_output_dir: str = ""

    CATEGORY = "JLNodes/latent"
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "load_latent"

    # -------------------------
    # UI
    # -------------------------
    @classmethod
    def INPUT_TYPES(cls):
        output_dir = folder_paths.get_output_directory()

        # Re-scan only if output dir changed or cache empty
        if cls._cached_output_dir != output_dir or not cls._cached_latents:
            cls._cached_latents = cls._scan_latents(output_dir)
            cls._cached_output_dir = output_dir

        latents = cls._cached_latents or [""]

        return {
            "required": {
                "latent_file": (latents,),
            }
        }

    # -------------------------
    # Core logic
    # -------------------------
    def load_latent(self, latent_file: str):
        if not latent_file:
            raise ValueError("No latent file selected")

        output_dir = folder_paths.get_output_directory()
        latent_path = os.path.join(output_dir, latent_file)

        if not os.path.isfile(latent_path):
            raise FileNotFoundError(f"Latent file not found: {latent_file}")

        try:
            data = safetensors.torch.load_file(latent_path, device="cpu")

            if "latent_tensor" not in data:
                raise KeyError("Missing 'latent_tensor' in latent file")

            latent_tensor = data["latent_tensor"].float()

            multiplier = cls._detect_multiplier(data)
            samples = {"samples": latent_tensor * multiplier}

            return (samples,)

        except Exception as e:
            print(f"[LoadLatent] Failed to load '{latent_file}': {e}")

            # Safe fallback to avoid graph crash
            return ({
                "samples": torch.zeros(DEFAULT_LATENT_SHAPE, dtype=torch.float32)
            },)

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _scan_latents(base_dir: str) -> List[str]:
        results = []

        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith(LATENT_EXT):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, base_dir)

                    # Normalize for ComfyUI dropdowns
                    results.append(rel_path.replace("\\", "/"))

        return sorted(results)

    @staticmethod
    def _detect_multiplier(data: dict) -> float:
        """
        Detect latent scale based on metadata.
        """
        # Future-proof: explicit version tags
        if "latent_format_version_0" in data:
            return 1.0

        # Default SD / SDXL VAE scaling
        return 1.0 / SD_VAE_SCALE

    # -------------------------
    # ComfyUI lifecycle hooks
    # -------------------------
    @classmethod
    def IS_CHANGED(cls, latent_file: str):
        if not latent_file:
            return "NO_FILE_SELECTED"

        output_dir = folder_paths.get_output_directory()
        latent_path = os.path.join(output_dir, latent_file)

        if not os.path.isfile(latent_path):
            return "FILE_MISSING"

        try:
            h = hashlib.sha256()
            with open(latent_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "HASH_ERROR"

    @classmethod
    def VALIDATE_INPUTS(cls, latent_file: str):
        if not latent_file:
            return "No latent file selected"

        output_dir = folder_paths.get_output_directory()
        latent_path = os.path.join(output_dir, latent_file)

        if not os.path.exists(latent_path):
            return f"Latent file not found: {latent_file}"

        return True


# -------------------------
# Node registration
# -------------------------
NODE_CLASS_MAPPINGS = {
    "LoadLatent": LoadLatent
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadLatent": "Load Latent"
}
