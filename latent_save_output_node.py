import os
import json
import torch
import comfy.utils
import folder_paths
from comfy.cli_args import args


class SaveAndOutputLatent:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "samples": ("LATENT",),
                "filename_prefix": ("STRING", {"default": "latents/ComfyUI"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    # 👇 IMPORTANT: return LATENT
    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)

    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "JLNodes/latent"

    def save(self, samples, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        # Resolve output path
        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir
            )

        # ---- metadata (same as official node) ----
        prompt_info = ""
        if prompt is not None:
            prompt_info = json.dumps(prompt)

        metadata = None
        if not args.disable_metadata:
            metadata = {"prompt": prompt_info}
            if extra_pnginfo is not None:
                for k, v in extra_pnginfo.items():
                    metadata[k] = json.dumps(v)

        # ---- filename ----
        latent_filename = f"{filename}_{counter:05}_.latent"
        latent_path = os.path.join(full_output_folder, latent_filename)

        # ---- save latent ----
        output = {
            "latent_tensor": samples["samples"].contiguous(),
            "latent_format_version_0": torch.tensor([]),
        }

        comfy.utils.save_torch_file(output, latent_path, metadata=metadata)

        # ---- UI result ----
        ui_results = [{
            "filename": latent_filename,
            "subfolder": subfolder,
            "type": "output",
        }]

        # 👇 RETURN BOTH UI INFO AND LATENT
        return {
            "ui": {"latents": ui_results},
            "result": (samples,)
        }

NODE_CLASS_MAPPINGS = {"SaveAndOutputLatent": SaveAndOutputLatent}
NODE_DISPLAY_NAME_MAPPINGS = {"SaveAndOutputLatent": "Save Latent (Save + Output)"}
