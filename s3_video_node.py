# s3_video_node.py
import os
import time

import boto3
import requests


class S3VideoNode:
    """
    Upload a local file (e.g., .mp4) to S3, return its URL, and optionally callback a Laravel endpoint.
    - Set `use_signed_url = True` to return a temporary presigned URL
      (no need to make the object public).
    - If `use_signed_url = False`, make sure your bucket/object ACL/policy allows public read.

    It can also take the Video Helper Suite output directly via 'vhs_filenames'.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "/path/to/video.mp4"}),
                "bucket": ("STRING", {"default": ""}),
                "key_template": ("STRING", {"default": "comfyui/videos/{basename}"}),  # supports {basename} and {timestamp}
                "region": ("STRING", {"default": ""}),
                "mime": ("STRING", {"default": "video/mp4"}),
                "use_signed_url": ("BOOLEAN", {"default": False}),
                "signed_expires": ("INT", {"default": 3600, "min": 60, "max": 604800}),
                "callback_url": ("STRING", {"default": ""}),  # you can append query params for tracking: ?job_id=...&image_id=...
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

    def _pick_path_from_vhs(self, vhs_filenames, prefer_index=-1):
        # Expected VHS structure: (save_output:boolean, [png_path, mp4_path, ...])
        try:
            if isinstance(vhs_filenames, (list, tuple)) and len(vhs_filenames) >= 2:
                paths = vhs_filenames[1]
                if isinstance(paths, (list, tuple)) and len(paths) > 0:
                    return str(paths[prefer_index])
        except Exception as e:
            print(f"[S3VideoNode] Could not parse VHS_FILENAMES: {e}")
        return None

    def upload(self, file_path, bucket, key_template, region, mime, use_signed_url, signed_expires, callback_url, vhs_filenames=None, prefer_index=-1):

        # If VHS output provided, pick the mp4 path from it
        if vhs_filenames is not None:
            picked = self._pick_path_from_vhs(vhs_filenames, prefer_index)
            if picked:
                file_path = picked

        # 1) Validate file
        file_path = (file_path or "").strip()
        if not os.path.isfile(file_path):
            print(f"[S3VideoNode] File not found: {file_path}")
            return ("",)

        # 2) Build S3 key
        basename = os.path.basename(file_path)
        timestamp = str(int(time.time()))
        key = (key_template or "").replace("{basename}", basename).replace("{timestamp}", timestamp)

        # 3) Read file bytes (simple & clear)
        with open(file_path, "rb") as f:
            data = f.read()

        # 4) Upload to S3
        s3 = boto3.client("s3", region_name=region or None)
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=mime)

        # 5) Build URL
        if use_signed_url:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=int(signed_expires) if signed_expires else 3600,
            )
        else:
            # url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}" if region else f"https://{bucket}.s3.amazonaws.com/{key}"
            url = f"https://{bucket}/{key}"

        print(f"[S3VideoNode] Uploaded {basename} -> {url}")

        # 6) Optional callback
        if callback_url:
            try:
                requests.post(
                    callback_url,
                    json={"url": url, "provider": "s3", "mime": mime, "size_bytes": len(data)},
                    timeout=20,
                )
            except Exception as e:
                print(f"[S3VideoNode] Callback failed: {e}")

        # 7) Return URL (works nicely with Display Any)
        return (url,)


NODE_CLASS_MAPPINGS = {"S3VideoNode": S3VideoNode}
NODE_DISPLAY_NAME_MAPPINGS = {"S3VideoNode": "S3 Upload (Video)"}
