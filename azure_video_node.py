# azure_video_node.py
import os
import time
import requests
from datetime import datetime, timedelta

# Optional: load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    BlobSasPermissions,
    generate_blob_sas,
)

class AzureVideoNode:
    """
    Upload a local VIDEO file (e.g., .mp4) to Azure Blob, return its URL,
    and optionally POST a callback to your Laravel endpoint.

    Auth priority:
      1) connection_string (node field)
      2) AZURE_STORAGE_CONNECTION_STRING (env)
      3) account_name + account_key (node fields)
      4) AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY (env)

    It can also take the Video Helper Suite output directly via 'vhs_filenames'.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "/home/azureuser/ComfyUI/output/video.mp4"}),
                "container_name": ("STRING", {"default": os.getenv("AZURE_BLOB_CONTAINER_VIDEOS", "videos")}),
                "blob_name_template": ("STRING", {"default": "comfyui/videos/{basename}"}),

                # Auth (leave blank to use .env)
                "connection_string": ("STRING", {"default": "", "multiline": True}),
                "account_name": ("STRING", {"default": ""}),
                "account_key": ("STRING", {"default": ""}),

                # Upload options
                "mime": ("STRING", {"default": "video/mp4"}),
                "use_signed_url": ("BOOLEAN", {"default": False}),
                "signed_expires": ("INT", {"default": 3600, "min": 60, "max": 604800}),
                "callback_url": ("STRING", {"default": ""}),
            },
            "optional": {
                # Wire this directly from VHS Video Combine if you want:
                "vhs_filenames": ("VHS_FILENAMES",),
                # -1 picks the last file (usually the final video). 0=first entry, 1=second, etc.
                "prefer_index": ("INT", {"default": -1, "min": -10, "max": 10}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("url",)
    FUNCTION = "upload"
    CATEGORY = "JLNodes/cloud"

    # ---------- helpers ----------
    def _get_service_client(self, connection_string, account_name, account_key):
        cs = (connection_string or "").strip() or os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
        if cs:
            return BlobServiceClient.from_connection_string(cs), None, None

        acct = (account_name or "").strip() or os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
        key  = (account_key  or "").strip() or os.getenv("AZURE_STORAGE_KEY", "").strip()
        if not acct or not key:
            raise ValueError(
                "Azure credentials missing: set connection_string OR account_name+account_key (or env vars)."
            )
        bsc = BlobServiceClient(account_url=f"https://{acct}.blob.core.windows.net", credential=key)
        return bsc, acct, key

    def _pick_path_from_vhs(self, vhs_filenames, prefer_index=-1):
        # Expected VHS structure: (save_output:boolean, [png_path, mp4_path, ...])
        try:
            if isinstance(vhs_filenames, (list, tuple)) and len(vhs_filenames) >= 2:
                paths = vhs_filenames[1]
                if isinstance(paths, (list, tuple)) and len(paths) > 0:
                    return str(paths[prefer_index])
        except Exception as e:
            print(f"[AzureVideoNode] Could not parse VHS_FILENAMES: {e}")
        return None

    # ---------- main ----------
    def upload(
        self,
        file_path,
        container_name,
        blob_name_template,
        connection_string,
        account_name,
        account_key,
        mime,
        use_signed_url,
        signed_expires,
        callback_url,
        vhs_filenames=None,
        prefer_index=-1,
    ):
        # If VHS output provided, pick the mp4 path from it
        if vhs_filenames is not None:
            picked = self._pick_path_from_vhs(vhs_filenames, prefer_index)
            if picked:
                file_path = picked

        file_path = (file_path or "").strip()
        if not os.path.isfile(file_path):
            print(f"[AzureVideoNode] File not found: {file_path}")
            return ("",)

        # Build client & container
        bsc, acct, key = self._get_service_client(connection_string, account_name, account_key)
        container = container_name.strip() or os.getenv("AZURE_BLOB_CONTAINER_VIDEOS", "videos")
        container_client = bsc.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass  # already exists

        basename = os.path.basename(file_path)
        timestamp = str(int(time.time()))
        blob_name = (blob_name_template or "comfyui/videos/{basename}") \
                        .replace("{basename}", basename) \
                        .replace("{timestamp}", timestamp)

        # Upload
        with open(file_path, "rb") as f:
            data = f.read()
        container_client.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            content_settings=ContentSettings(content_type=mime),
        )

        # URL (public if container access is Blob; otherwise use SAS)
        url = f"{container_client.url}/{blob_name}"

        if use_signed_url:
            if acct is None:
                acct = bsc.account_name
            if not key:
                key = os.getenv("AZURE_STORAGE_KEY", "")
            if not key:
                raise ValueError("AZURE_STORAGE_KEY required to generate SAS when use_signed_url=True.")
            sas = generate_blob_sas(
                account_name=acct,
                container_name=container,
                blob_name=blob_name,
                account_key=key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=int(signed_expires)),
            )
            url = f"{url}?{sas}"

        # Optional callback
        if callback_url:
            try:
                requests.post(
                    callback_url,
                    json={"url": url, "provider": "azure", "mime": mime, "size_bytes": len(data)},
                    timeout=20,
                )
            except Exception as e:
                print(f"[AzureVideoNode] Callback failed: {e}")

        return (url,)


NODE_CLASS_MAPPINGS = {"AzureVideoNode": AzureVideoNode}
NODE_DISPLAY_NAME_MAPPINGS = {"AzureVideoNode": "Azure Upload (Video)"}
