import os
import json
import base64
import torch
import folder_paths


# ------------------------------
# Decode helpers
# ------------------------------

def decode_tensor(obj):
    raw = base64.b64decode(obj["data"])

    # FIX: dtype may come as "torch.float32"
    dtype_str = obj["dtype"]
    if dtype_str.startswith("torch."):
        dtype_str = dtype_str.replace("torch.", "")

    dtype = getattr(torch, dtype_str)

    tensor = torch.frombuffer(raw, dtype=dtype).reshape(obj["shape"])
    return tensor


def decode_obj(obj):
    """Recursively decode list/dict/tensor/value structures."""

    t = obj["type"]

    if t == "tensor":
        return decode_tensor(obj)

    elif t == "value":
        return obj["data"]

    elif t == "list":
        return [decode_obj(x) for x in obj["data"]]

    elif t == "dict":
        return {k: decode_obj(v) for k, v in obj["data"].items()}

    else:
        raise ValueError(f"Unknown type in JSON: {t}")


# ------------------------------
# Load Node
# ------------------------------

class ConditioningLoadJSONNode:
    @classmethod
    def INPUT_TYPES(cls):
        cond_dir = os.path.join(folder_paths.output_directory, "conditioning")
        files = []
        if os.path.exists(cond_dir):
            files = [f for f in os.listdir(cond_dir) if f.endswith(".json")]

        return {
            "required": {
                "filename": (files,),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    CATEGORY = "JLNodes/conditioning"
    FUNCTION = "load"

    def load(self, filename):
        full_path = os.path.join(folder_paths.output_directory, "conditioning", filename)

        with open(full_path, "r") as f:
            entries = json.load(f)

        output = []

        for entry in entries:
            tensor_part = decode_tensor(entry["tensor"])
            meta_part = decode_obj(entry["meta"])

            # MUST return structure EXACTLY like ComfyUI:
            #   list of [ tensor , dict ]
            output.append([tensor_part, meta_part])

        print(f"[ConditioningLoadJSONNode] Loaded ← {full_path}")
        return (output,)


NODE_CLASS_MAPPINGS = {"ConditioningLoadJSONNode": ConditioningLoadJSONNode}
NODE_DISPLAY_NAME_MAPPINGS = {"ConditioningLoadJSONNode": "Load Conditioning (JSON)"}