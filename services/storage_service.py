"""
services/storage_service.py

Abstract storage interface and Supabase Storage implementation.

The Instagram publisher receives only List[str] of public URLs.
It never knows the storage provider. Swapping to S3, Cloudinary,
or Firebase later requires only a new class — zero Instagram changes.
"""

import os
import logging
import mimetypes
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

import requests

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_BUCKET,
)


logger = logging.getLogger(__name__)


# ==========================================================
# Abstract Storage Interface
# ==========================================================

class StorageService(ABC):
    """
    Abstract storage interface.

    Every storage backend must implement these methods.
    Instagram and the publishing pipeline depend only on this
    interface, never on a concrete implementation.
    """

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> Dict[str, Any]:
        """
        Upload a single file.

        Returns:
            {
                "success": bool,
                "filename": str,
                "remote_path": str,
                "public_url": str,
            }
        """
        pass

    @abstractmethod
    def upload_folder(
        self,
        local_folder: str,
        remote_prefix: str,
        max_workers: int = 3,
    ) -> Dict[str, Any]:
        """
        Upload all files in a local folder concurrently.

        Returns:
            {
                "success": bool,
                "urls": List[str],   (sorted by filename)
                "files": List[dict],
                "error": str or None,
            }
        """
        pass

    @abstractmethod
    def get_public_url(
        self,
        remote_path: str,
    ) -> str:
        """Return the public URL for a remote path."""
        pass

    @abstractmethod
    def verify_url(
        self,
        url: str,
        timeout: int = 15,
    ) -> bool:
        """
        Verify a URL is publicly accessible and serves image content.

        Checks:
        - HTTP 200
        - Content-Type begins with image/
        """
        pass

    @abstractmethod
    def delete_folder(
        self,
        remote_prefix: str,
    ) -> bool:
        """Delete all files under a remote prefix."""
        pass


# ==========================================================
# Supabase Storage Implementation
# ==========================================================

class SupabaseStorage(StorageService):
    """
    Supabase Storage implementation using the REST API.

    Uses the existing `requests` library — zero new SDK dependencies.
    Uploads with the Service Role Key for write access.
    Public URLs are deterministic for public buckets.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        self.url = (url or SUPABASE_URL).rstrip("/")
        self.key = key or SUPABASE_SERVICE_ROLE_KEY
        self.bucket = bucket or SUPABASE_BUCKET
        self.storage_url = f"{self.url}/storage/v1"

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "must be set in environment variables."
            )

    def _get_headers(
        self,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, str]:
        """Build authorization headers for Supabase Storage API."""
        return {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

    def _detect_content_type(
        self,
        filepath: str,
    ) -> str:
        """Detect MIME type from file extension."""
        mime_type, _ = mimetypes.guess_type(filepath)
        return mime_type or "application/octet-stream"

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> Dict[str, Any]:
        """
        Upload a single file to Supabase Storage.

        Uses x-upsert: true to handle re-uploads gracefully.
        """
        filename = os.path.basename(local_path)
        content_type = self._detect_content_type(local_path)
        url = f"{self.storage_url}/object/{self.bucket}/{remote_path}"

        logger.info(
            f"Uploading {filename} -> {remote_path} "
            f"({content_type})"
        )

        try:
            with open(local_path, "rb") as f:
                response = requests.post(
                    url,
                    headers=self._get_headers(content_type),
                    data=f,
                    timeout=60,
                )

            if response.status_code in (200, 201):
                public_url = self.get_public_url(remote_path)
                logger.info(f"  ✓ Uploaded {filename}")
                return {
                    "success": True,
                    "filename": filename,
                    "remote_path": remote_path,
                    "public_url": public_url,
                }

            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("message", error_msg)
            except Exception:
                pass

            logger.error(
                f"  ✗ Upload failed for {filename}: "
                f"HTTP {response.status_code} — {error_msg}"
            )
            return {
                "success": False,
                "filename": filename,
                "remote_path": remote_path,
                "public_url": "",
                "error": error_msg,
            }

        except Exception as exc:
            logger.error(
                f"  ✗ Upload exception for {filename}: {exc}"
            )
            return {
                "success": False,
                "filename": filename,
                "remote_path": remote_path,
                "public_url": "",
                "error": str(exc),
            }

    def upload_folder(
        self,
        local_folder: str,
        remote_prefix: str,
        max_workers: int = 3,
    ) -> Dict[str, Any]:
        """
        Upload all image files in a local folder concurrently.

        Uses ThreadPoolExecutor with a configurable worker limit
        (default 3) to avoid overwhelming Supabase.

        Returns URLs sorted by filename to preserve slide order.
        """
        if not os.path.isdir(local_folder):
            return {
                "success": False,
                "urls": [],
                "files": [],
                "error": f"Folder not found: {local_folder}",
            }

        files = sorted(os.listdir(local_folder))
        if not files:
            return {
                "success": False,
                "urls": [],
                "files": [],
                "error": f"No files in folder: {local_folder}",
            }

        logger.info(
            f"Uploading {len(files)} files from "
            f"{local_folder} -> {remote_prefix} "
            f"(max_workers={max_workers})"
        )

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = {}

            for filename in files:
                local_path = os.path.join(local_folder, filename)

                if not os.path.isfile(local_path):
                    continue

                remote_path = f"{remote_prefix}/{filename}"

                future = executor.submit(
                    self.upload_file,
                    local_path,
                    remote_path,
                )
                futures[future] = filename

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    filename = futures[future]
                    logger.error(
                        f"  ✗ Thread exception for "
                        f"{filename}: {exc}"
                    )
                    results.append({
                        "success": False,
                        "filename": filename,
                        "remote_path": "",
                        "public_url": "",
                        "error": str(exc),
                    })

        # Sort by filename to preserve slide order
        results.sort(key=lambda r: r.get("filename", ""))

        failed = [r for r in results if not r.get("success")]
        if failed:
            failed_names = [r["filename"] for r in failed]
            logger.error(
                f"Upload failed for: {', '.join(failed_names)}"
            )
            return {
                "success": False,
                "urls": [],
                "files": results,
                "error": (
                    f"Failed uploads: {', '.join(failed_names)}"
                ),
            }

        urls = [r["public_url"] for r in results]
        logger.info(
            f"All {len(urls)} files uploaded successfully."
        )
        return {
            "success": True,
            "urls": urls,
            "files": results,
            "error": None,
        }

    def get_public_url(
        self,
        remote_path: str,
    ) -> str:
        """
        Construct the deterministic public URL for a file.

        Requires the bucket to be configured as Public
        in the Supabase Dashboard.
        """
        return (
            f"{self.url}/storage/v1/object/public/"
            f"{self.bucket}/{remote_path}"
        )

    def verify_url(
        self,
        url: str,
        timeout: int = 15,
    ) -> bool:
        """
        Verify a URL is publicly reachable and serves image content.

        Instagram's servers will make a similar request to fetch
        the image for publishing. If this check fails, Instagram
        will also fail.
        """
        try:
            response = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
            )

            if response.status_code in (405, 403) or response.status_code != 200:
                logger.warning(
                    f"HEAD request returned HTTP {response.status_code} for {url}, "
                    "falling back to GET stream=True..."
                )
                response = requests.get(
                    url,
                    stream=True,
                    timeout=timeout,
                    allow_redirects=True,
                )
                response.close()

            if response.status_code != 200:
                logger.error(
                    f"Verification failed for {url}: "
                    f"HTTP {response.status_code}"
                )
                return False

            content_type = response.headers.get(
                "Content-Type", ""
            )

            if not content_type.startswith("image/"):
                logger.error(
                    f"Verification failed for {url}: "
                    f"Content-Type is '{content_type}', "
                    f"expected image/*"
                )
                return False

            logger.info(f"  ✓ Verified {url}")
            return True

        except Exception as exc:
            logger.warning(
                f"HEAD verification exception for {url}: {exc}, falling back to GET stream=True..."
            )
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=timeout,
                    allow_redirects=True,
                )
                response.close()
                if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    logger.info(f"  ✓ Verified {url} via GET fallback")
                    return True
            except Exception as get_exc:
                logger.error(
                    f"Verification fallback exception for {url}: {get_exc}"
                )
            return False


    def delete_folder(
        self,
        remote_prefix: str,
    ) -> bool:
        """
        Delete all files under a remote prefix.

        Exposed for future cleanup automation.
        Not used in the current publishing pipeline.
        """
        url = f"{self.storage_url}/object/{self.bucket}"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
            "Content-Type": "application/json",
        }

        # List files under prefix first
        list_url = (
            f"{self.storage_url}/object/list/{self.bucket}"
        )
        list_body = {
            "prefix": remote_prefix,
            "limit": 100,
        }

        try:
            list_resp = requests.post(
                list_url,
                headers=headers,
                json=list_body,
                timeout=30,
            )

            if list_resp.status_code != 200:
                logger.error(
                    f"Failed to list files for deletion: "
                    f"{list_resp.text}"
                )
                return False

            files = list_resp.json()
            if not files:
                logger.info(
                    f"No files to delete under {remote_prefix}"
                )
                return True

            file_paths = [
                f"{remote_prefix}/{f['name']}"
                for f in files
            ]

            delete_resp = requests.delete(
                url,
                headers=headers,
                json={"prefixes": file_paths},
                timeout=30,
            )

            if delete_resp.status_code == 200:
                logger.info(
                    f"Deleted {len(file_paths)} files "
                    f"under {remote_prefix}"
                )
                return True

            logger.error(
                f"Delete failed: {delete_resp.text}"
            )
            return False

        except Exception as exc:
            logger.error(
                f"Delete exception for {remote_prefix}: {exc}"
            )
            return False
