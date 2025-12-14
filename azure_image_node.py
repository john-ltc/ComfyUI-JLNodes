# azure_image_node.py
import io, os, time
import requests
from datetime import datetime, timedelta

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    BlobSasPermissions,
    generate_blob_sas,
)

# optional: if python-dotenv is installed, we'll load .env automatically (won't error if missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class AzureImageNode:
    """
    Upload an IMAGE tensor (PNG) to Azure Blob, return (image, url), and optionally POST a callback.

    Priority for credentials:
      1) connection_string (node field)
      2) env AZURE_STORAGE_CONNECTION_STRING
      3) account_name + account_key (node fields)
      4) env AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "container_name": ("STRING", {"default": "images"}),
                "blob_name_template": ("STRING", {"default": "comfyui/images/{timestamp}.png"}),
                # Provide either connection_string OR (account_name + account_key), or leave blank to use env.
                "connection_string": ("STRING", {"default": "", "multiline": True}),
                "account_name": ("STRING", {"default": ""}),
                "account_key": ("STRING", {"default": ""}),
                "mime": ("STRING", {"default": "image/png"}),
                "use_signed_url": ("BOOLEAN", {"default": False}),
                "signed_expires": ("INT", {"default": 3600, "min": 60, "max": 604800}),
                "callback_url": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "url")
    FUNCTION = "upload"
    CATEGORY = "JLNodes/cloud"

    # ---- helpers ----
    def _get_service_client(self, connection_string, account_name, account_key):
        cs = (connection_string or "").strip() or os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
        if cs:
            return BlobServiceClient.from_connection_string(cs), None, None

        acct = (account_name or "").strip() or os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
        key  = (account_key  or "").strip() or os.getenv("AZURE_STORAGE_KEY", "").strip()
        if not acct or not key:
            raise ValueError("Azure credentials missing: set connection_string OR account_name+account_key (or env).")
        bsc = BlobServiceClient(account_url=f"https://{acct}.blob.core.windows.net", credential=key)
        return bsc, acct, key

    def _tensor_to_png_bytes(self, image):
        from PIL import Image
        import numpy as np
        arr = image[0].cpu().numpy()
        arr = (np.clip(arr, 0, 1) * 255).astype("uint8")
        pil = Image.fromarray(arr)
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        return buf.getvalue()

    # ---- main ----
    def upload(
        self,
        image,
        container_name,
        blob_name_template,
        connection_string,
        account_name,
        account_key,
        mime,
        use_signed_url,
        signed_expires,
        callback_url,
    ):
        # 1) prepare bytes
        data = self._tensor_to_png_bytes(image)
        timestamp = str(int(time.time()))
        blob_name = blob_name_template.replace("{timestamp}", timestamp)

        # 2) client/container
        bsc, acct, key = self._get_service_client(connection_string, account_name, account_key)
        container_client = bsc.get_container_client(container_name.strip() or "images")
        try:
            container_client.create_container()
        except Exception:
            pass  # already exists

        # 3) upload
        container_client.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            content_settings=ContentSettings(content_type=mime),
        )

        # 4) build URL (public if container access level = Blob)
        url = f"{container_client.url}/{blob_name}"
        path = blob_name

        # 5) optional SAS
        if use_signed_url:
            if acct is None:
                acct = bsc.account_name
            if not key:
                key = os.getenv("AZURE_STORAGE_KEY", "")
            if not key:
                raise ValueError("AZURE_STORAGE_KEY required to generate SAS when use_signed_url=True.")
            sas = generate_blob_sas(
                account_name=acct,
                container_name=container_name,
                blob_name=blob_name,
                account_key=key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=int(signed_expires)),
            )
            url = f"{url}?{sas}"

        # 6) optional callback
        if callback_url:
            try:
                requests.post(
                    callback_url,
                    json={"url": url, "path": path, "provider": "azure", "mime": mime, "size_bytes": len(data)},
                    timeout=20,
                )
            except Exception as e:
                print(f"[AzureImageNode] Callback failed: {e}")

        # 7) passthrough image + url
        return (image, url)


NODE_CLASS_MAPPINGS = {"AzureImageNode": AzureImageNode}
NODE_DISPLAY_NAME_MAPPINGS = {"AzureImageNode": "Azure Upload (Image)"}
