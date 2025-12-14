import io, os, time
from PIL import Image
import numpy as np
import boto3, requests

class S3ImageNode:
    """
    Upload an IMAGE tensor as PNG to S3, return its URL, and optionally callback a Laravel endpoint.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "bucket": ("STRING", {"default": ""}),
                "key_template": ("STRING", {"default": "comfy/{timestamp}.png"}),
                "region": ("STRING", {"default": ""}),
                "mime": ("STRING", {"default": "image/png"}),
                "use_signed_url": ("BOOLEAN", {"default": False}),
                "callback_url": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "url")
    FUNCTION = "upload"
    CATEGORY = "JLNodes/cloud"

    def upload(self, image, bucket, key_template, region, mime, use_signed_url, callback_url):
        key = key_template.replace("{timestamp}", str(int(time.time())))
        path = key

        # Convert image tensor → PNG bytes
        arr = image[0].cpu().numpy()
        arr = (np.clip(arr, 0, 1) * 255).astype("uint8")
        pil = Image.fromarray(arr)
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        buf.seek(0)
        data = buf.getvalue()

        # Upload to S3
        s3 = boto3.client("s3", region_name=region or None)
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=mime)

        # Get URL
        if use_signed_url:
            url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
        else:
            # url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}" if region else f"https://{bucket}.s3.amazonaws.com/{key}"
            url = f"https://{bucket}/{key}"

        # Optional callback
        if callback_url:
            try:
                requests.post(callback_url, json={"url": url, "path": path, "provider": "s3"})
            except Exception as e:
                print(f"[S3ImageNode] Callback failed: {e}")

        return (image, url)

NODE_CLASS_MAPPINGS = {"S3ImageNode": S3ImageNode}
NODE_DISPLAY_NAME_MAPPINGS = {"S3ImageNode": "S3 Upload (Image)"}
