import os
import json
import base64
import torch
import folder_paths


# ------------------------------
# Encoding helpers
# ------------------------------

def encode_tensor(t):
    t = t.detach().cpu()
    return {
        "type": "tensor",
        "data": base64.b64encode(t.numpy().tobytes()).decode("utf-8"),
        "shape": list(t.shape),
        "dtype": str(t.dtype)
    }


def encode_obj(v):
    """Recursively encode ALL tensors inside metadata."""
    
    # Tensor → encode
    if torch.is_tensor(v):
        return encode_tensor(v)

    # List / tuple → recursively encode elements
    if isinstance(v, (list, tuple)):
        return {
            "type": "list",
            "data": [encode_obj(x) for x in v]
        }

    # Dict → recursively encode values
    if isinstance(v, dict):
        return {
            "type": "dict",
            "data": {k: encode_obj(val) for k, val in v.items()}
        }

    # Anything else → store as normal value
    return {
        "type": "value",
        "data": v
    }


# ------------------------------
# Save Node
# ------------------------------

class ConditioningSaveJSONNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("CONDITIONING",),
                "filename": ("STRING", {"default": "conditioning.json"})
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    CATEGORY = "JLNodes/conditioning"
    FUNCTION = "save"

    def save(self, conditioning, filename):

        out_dir = os.path.join(folder_paths.output_directory, "conditioning")
        os.makedirs(out_dir, exist_ok=True)
        full_path = os.path.join(out_dir, filename)

        data_out = []

        for item in conditioning:
            tensor_part = item[0]      # torch.Tensor
            meta_part = item[1]        # dict containing tensors

            encoded_meta = encode_obj(meta_part)

            data_out.append({
                "tensor": encode_tensor(tensor_part),
                "meta": encoded_meta
            })

        with open(full_path, "w") as f:
            json.dump(data_out, f)

        print(f"[ConditioningSaveJSONNode] Saved → {full_path}")
        return {}


NODE_CLASS_MAPPINGS = {"ConditioningSaveJSONNode": ConditioningSaveJSONNode}
NODE_DISPLAY_NAME_MAPPINGS = {"ConditioningSaveJSONNode": "Save Conditioning (JSON)"}