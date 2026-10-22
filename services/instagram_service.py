"""
services/instagram_service.py

Production Instagram Graph API carousel publisher.

Responsibilities:
- Create individual media containers for carousel slides
- Create parent CAROUSEL container
- Poll container processing status
- Publish carousel to Instagram feed
- Retrieve post permalink after publishing

This service receives only List[str] of public image URLs.
It never knows the storage backend.
"""

import time
import logging
from typing import List, Dict, Any, Optional

import requests

from config.app_config import config


logger = logging.getLogger(__name__)


# ==========================================================
# Transient Error Codes (Safe to Retry)
# ==========================================================

TRANSIENT_ERROR_CODES = {4, 17, 32, 613}


class InstagramService:
    """
    Production Instagram Graph API publisher.

    Handles carousel creation, container status polling,
    publishing, and permalink retrieval with structured
    logging and exponential backoff.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        ig_user_id: Optional[str] = None,
        page_id: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.access_token = (
            access_token or config.services.instagram.access_token
        )
        self.ig_user_id = (
            ig_user_id or config.services.instagram.business_account_id
        )
        self.page_id = page_id or config.services.instagram.facebook_page_id
        self.api_version = api_version or config.services.instagram.graph_api_version
        self.base_url = (
            f"https://graph.facebook.com/{self.api_version}"
        )

        if not self.access_token or not self.ig_user_id:
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN and "
                "INSTAGRAM_BUSINESS_ACCOUNT_ID must be set "
                "in environment variables."
            )

    # --------------------------------------------------
    # HTTP Request Helper
    # --------------------------------------------------

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute a Graph API request with exponential backoff
        on transient errors (codes 4, 17, 32, 613).

        Logs fbtrace_id on failures for Meta support
        escalation.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        request_params = params.copy() if params else {}
        request_params["access_token"] = self.access_token

        for attempt in range(1, max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(
                        url,
                        params=request_params,
                        timeout=timeout,
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url,
                        params=request_params,
                        json=json_data,
                        timeout=timeout,
                    )
                else:
                    raise ValueError(
                        f"Unsupported HTTP method: {method}"
                    )

                data = response.json()

                # Extract fbtrace_id for debugging
                fbtrace_id = response.headers.get(
                    "x-fb-trace-id", "N/A"
                )

                if (
                    response.status_code == 200
                    and "error" not in data
                ):
                    return data

                error = data.get("error", {})
                code = error.get("code")
                subcode = error.get("error_subcode")
                message = error.get("message", "Unknown error")
                error_type = error.get("type", "OAuthException")

                if (
                    code in TRANSIENT_ERROR_CODES
                    and attempt < max_retries
                ) or (code == 9 and subcode == 2207085 and attempt < 3):
                    if code == 9 and subcode == 2207085:
                        delay = 300 if attempt == 1 else 600
                        logger.warning(
                            f"Rate Limit error [{code}:{subcode}]: {message}. "
                            f"Retrying in {delay}s "
                            f"(attempt {attempt}/3) "
                            f"[fbtrace_id={fbtrace_id}]"
                        )
                    else:
                        delay = 2 ** attempt
                        logger.warning(
                            f"Transient error [{code}:{subcode}]: {message}. "
                            f"Retrying in {delay}s "
                            f"(attempt {attempt}/{max_retries}) "
                            f"[fbtrace_id={fbtrace_id}]"
                        )
                    time.sleep(delay)
                    continue

                logger.error(
                    f"Graph API Error [{method} {endpoint}] "
                    f"Code: {code}, Subcode: {subcode}, "
                    f"Type: {error_type}, "
                    f"Message: {message} "
                    f"[fbtrace_id={fbtrace_id}]"
                )
                return {
                    "error": {
                        "code": code,
                        "subcode": subcode,
                        "message": message,
                        "fbtrace_id": fbtrace_id,
                    }
                }

            except requests.exceptions.RequestException as exc:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    logger.warning(
                        f"Network error: {exc}. "
                        f"Retrying in {delay}s "
                        f"(attempt {attempt}/{max_retries})"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Max retries exceeded for "
                        f"[{method} {endpoint}]: {exc}"
                    )
                    return {
                        "error": {
                            "code": -1,
                            "message": str(exc),
                            "fbtrace_id": "N/A",
                        }
                    }

        return {
            "error": {
                "code": -1,
                "message": "Max retry attempts exhausted",
                "fbtrace_id": "N/A",
            }
        }

    # --------------------------------------------------
    # Send Direct Message
    # --------------------------------------------------

    def send_message(self, recipient_id: str, text: str) -> "MessageResult":
        """
        Sends a Direct Message to an Instagram user using the Messaging API.

        POST /{page_id}/messages or /me/messages
          recipient={"id": "<IGSID>"}
          message={"text": "..."}
        """
        from features.engagement.models import MessageResult

        logger.info(f"Sending DM to {recipient_id}...")

        # Meta expects the endpoint on the Page ID (or /me which resolves to page)
        # when using Page Access Token with IG Messaging API
        endpoint = f"{self.page_id}/messages" if self.page_id else "me/messages"

        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }

        response = self._make_request(
            "POST",
            endpoint,
            json_data=payload
        )

        if "error" in response:
            error = response["error"]
            code = error.get("code")
            return MessageResult(
                success=False,
                message_id=None,
                error_code=str(code),
                error_message=error.get("message", "Unknown error"),
                retryable=code in TRANSIENT_ERROR_CODES,
                http_status=None,
                raw_response=str(error)
            )

        message_id = response.get("message_id")
        if not message_id:
            return MessageResult(
                success=False,
                message_id=None,
                error_code="-1",
                error_message=f"No message_id in response: {response}",
                retryable=False,
                http_status=None,
                raw_response=str(response)
            )

        logger.info(f"  ✓ DM Sent! Message ID: {message_id}")
        return MessageResult(
            success=True,
            message_id=message_id,
            error_code=None,
            error_message=None,
            retryable=False,
            http_status=200,
            raw_response=None
        )

    # --------------------------------------------------
    # Create Media Container (Single Slide)
    # --------------------------------------------------

    def create_media_container(
        self,
        image_url: str,
    ) -> Dict[str, Any]:
        """
        Create an Instagram media container for one
        carousel slide.

        POST /{ig-user-id}/media
          image_url=...
          is_carousel_item=true

        Returns:
            {"success": True, "container_id": str}
            or
            {"success": False, "error": str}
        """
        logger.info(
            f"Creating media container: {image_url[:80]}..."
        )

        response = self._make_request(
            "POST",
            f"{self.ig_user_id}/media",
            params={
                "image_url": image_url,
                "is_carousel_item": "true",
            },
        )

        if "error" in response:
            error = response["error"]
            return {
                "success": False,
                "error": error.get("message", str(error)),
                "fbtrace_id": error.get("fbtrace_id", "N/A"),
            }

        container_id = response.get("id")
        if not container_id:
            return {
                "success": False,
                "error": f"No ID in response: {response}",
            }

        logger.info(
            f"  ✓ Container created: {container_id}"
        )
        return {
            "success": True,
            "container_id": container_id,
        }

    # --------------------------------------------------
    # Check Container Status
    # --------------------------------------------------

    def check_container_status(
        self,
        container_id: str,
    ) -> str:
        """
        Check the processing status of a media container.

        GET /{container-id}?fields=status_code

        Returns one of:
        FINISHED, IN_PROGRESS, EXPIRED, ERROR, PUBLISHED
        """
        response = self._make_request(
            "GET",
            container_id,
            params={"fields": "status_code"},
        )

        if "error" in response:
            return "ERROR"

        return response.get("status_code", "UNKNOWN").upper()

    # --------------------------------------------------
    # Wait for Container
    # --------------------------------------------------

    def wait_for_container(
        self,
        container_id: str,
        max_wait_seconds: int = 120,
        poll_interval: int = 5,
    ) -> bool:
        """
        Poll container status until FINISHED or terminal state.

        Returns True if container reached FINISHED.
        Returns False if container reached ERROR/EXPIRED
        or timed out.
        """
        logger.info(
            f"Waiting for container {container_id}..."
        )

        elapsed = 0

        while elapsed < max_wait_seconds:

            status = self.check_container_status(container_id)

            if status == "FINISHED":
                logger.info(
                    f"  ✓ Container {container_id} → FINISHED"
                )
                return True

            if status in ("EXPIRED", "ERROR"):
                logger.error(
                    f"  ✗ Container {container_id} → {status}"
                )
                return False

            time.sleep(poll_interval)
            elapsed += poll_interval

        logger.error(
            f"  ✗ Container {container_id} timed out "
            f"after {max_wait_seconds}s"
        )
        return False

    # --------------------------------------------------
    # Create Carousel Container
    # --------------------------------------------------

    def create_carousel(
        self,
        container_ids: List[str],
        caption: str = "",
    ) -> Dict[str, Any]:
        """
        Create the parent CAROUSEL container linking
        child containers.

        POST /{ig-user-id}/media
          media_type=CAROUSEL
          children=id1,id2,...
          caption=...

        Returns:
            {"success": True, "creation_id": str}
            or
            {"success": False, "error": str}
        """
        if len(container_ids) < 2 or len(container_ids) > 10:
            return {
                "success": False,
                "error": (
                    "Carousel requires 2-10 children. "
                    f"Got {len(container_ids)}."
                ),
            }

        logger.info(
            f"Creating carousel container with "
            f"{len(container_ids)} slides..."
        )

        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(container_ids),
        }

        if caption:
            params["caption"] = caption

        response = self._make_request(
            "POST",
            f"{self.ig_user_id}/media",
            params=params,
        )

        if "error" in response:
            error = response["error"]
            return {
                "success": False,
                "error": error.get("message", str(error)),
                "fbtrace_id": error.get("fbtrace_id", "N/A"),
            }

        creation_id = response.get("id")
        if not creation_id:
            return {
                "success": False,
                "error": f"No ID in response: {response}",
            }

        logger.info(
            f"  ✓ Carousel container created: {creation_id}"
        )
        return {
            "success": True,
            "creation_id": creation_id,
        }

    # --------------------------------------------------
    # Publish
    # --------------------------------------------------

    def publish(
        self,
        creation_id: str,
    ) -> Dict[str, Any]:
        """
        Publish a ready container to Instagram.

        POST /{ig-user-id}/media_publish
          creation_id=...

        Returns:
            {"success": True, "media_id": str}
            or
            {"success": False, "error": str}
        """
        logger.info(
            f"Publishing container {creation_id}..."
        )

        response = self._make_request(
            "POST",
            f"{self.ig_user_id}/media_publish",
            params={"creation_id": creation_id},
        )

        if "error" in response:
            error = response["error"]
            return {
                "success": False,
                "error": error.get("message", str(error)),
                "fbtrace_id": error.get("fbtrace_id", "N/A"),
            }

        media_id = response.get("id")
        if not media_id:
            return {
                "success": False,
                "error": f"No ID in response: {response}",
            }

        logger.info(
            f"  ✓ PUBLISHED SUCCESSFULLY! "
            f"Media ID: {media_id}"
        )
        return {
            "success": True,
            "media_id": media_id,
        }

    # --------------------------------------------------
    # Check Publishing Limit
    # --------------------------------------------------

    def check_publishing_limit(self) -> Dict[str, Any]:
        """
        Check the publishing quota limit.
        GET /{ig-user-id}/content_publishing_limit
        """
        response = self._make_request(
            "GET",
            f"{self.ig_user_id}/content_publishing_limit",
            params={"fields": "config,quota_usage"}
        )
        if "error" in response:
            return {"success": False, "error": response["error"]}

        data = response.get("data", [])
        if not data:
            return {"success": True, "quota_usage": 0, "quota_total": 25}

        usage = data[0].get("quota_usage", 0)
        total = data[0].get("config", {}).get("quota_total", 25)

        logger.info(f"Instagram Publishing Quota: {usage}/{total} used.")
        return {"success": True, "quota_usage": usage, "quota_total": total}

    # --------------------------------------------------
    # Get Permalink
    # --------------------------------------------------

    def get_permalink(
        self,
        media_id: str,
    ) -> str:
        """
        Retrieve the Instagram post URL after publishing.

        GET /{media-id}?fields=permalink

        Returns the permalink string, or empty string on failure.
        """
        response = self._make_request(
            "GET",
            media_id,
            params={"fields": "permalink"},
        )

        if "error" in response:
            logger.warning(
                f"Could not retrieve permalink for "
                f"{media_id}: {response['error']}"
            )
            return ""

        permalink = response.get("permalink", "")
        if permalink:
            logger.info(
                f"  ✓ Permalink: {permalink}"
            )
        return permalink

    # --------------------------------------------------
    # Verify Publication Exists on Server
    # --------------------------------------------------

    def verify_publication(
        self,
        media_id: str,
        max_retries: int = 5,
        retry_delay: int = 3,
    ) -> Dict[str, Any]:
        """
        Verify that a published media object actually exists on Instagram
        and is queryable via Graph API before writing metadata to Sheets.

        GET /{media-id}?fields=id,permalink,media_type,timestamp
        """
        logger.info(f"Verifying published object exists on Instagram: {media_id}...")
        for attempt in range(1, max_retries + 1):
            response = self._make_request(
                "GET",
                media_id,
                params={"fields": "id,permalink,media_type,timestamp"},
            )
            if "error" not in response and response.get("id") == media_id:
                logger.info(f"  ✓ Verified published object {media_id} exists on Instagram (Attempt {attempt})")
                return {
                    "verified": True,
                    "permalink": response.get("permalink", ""),
                    "media_type": response.get("media_type", ""),
                    "timestamp": response.get("timestamp", ""),
                }
            logger.warning(f"Publication verification attempt {attempt}/{max_retries} did not confirm object yet. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

        logger.error(f"  ✗ Could not verify published object {media_id} after {max_retries} attempts.")
        return {"verified": False, "permalink": ""}

    # --------------------------------------------------
    # Publish Carousel (Full Orchestrator)
    # --------------------------------------------------



    def publish_carousel(
        self,
        generation_id: str,
        image_urls: List[str],
        attempt_repo: 'InstagramPublicationAttemptRepository',
        caption: str = "",
    ) -> Dict[str, Any]:
        """
        Full carousel publishing orchestration enforcing strict monotonic fail-closed states.
        """
        import requests

        attempt = attempt_repo.get_attempt(generation_id)

        container_ids = []
        creation_id = None

        if attempt:
            state = attempt['publish_state']
            if state in ('PUBLISH_OUTCOME_UNKNOWN', 'PUBLISHED_MEDIA_KNOWN', 'PUBLISHED_VERIFIED'):
                logger.error(f"Cannot publish {generation_id}: Attempt state is {state}. Manual reconciliation required.")
                return {"success": False, "error": f"Attempt state is {state}. Manual reconciliation required."}
            elif state == 'PUBLISH_REQUESTED':
                logger.error(f"Cannot publish {generation_id}: Attempt state is PUBLISH_REQUESTED (ambiguous crash state). Transitioning to PUBLISH_OUTCOME_UNKNOWN.")
                attempt_repo.transition_state(generation_id, 'PUBLISH_OUTCOME_UNKNOWN')
                return {"success": False, "error": "PUBLISH_REQUESTED found on retry. Transitioned to PUBLISH_OUTCOME_UNKNOWN."}
            elif state == 'PUBLISH_RETRY_AUTHORIZED':
                creation_id = attempt.get('carousel_creation_id')
                if not creation_id:
                    return {"success": False, "error": "PUBLISH_RETRY_AUTHORIZED missing carousel_creation_id"}
                logger.info(f"Resuming authorized retry using existing carousel {creation_id}")
            else:
                return {"success": False, "error": f"Unhandled attempt state: {state}"}
        else:
            # Step 1: Create item containers
            slide_count = len(image_urls)
            if slide_count < 2 or slide_count > 10:
                return {"success": False, "error": f"Instagram carousels require 2-10 images. Got {slide_count}."}

            for idx, url in enumerate(image_urls, start=1):
                logger.info(f"Slide {idx}/{slide_count}...")
                result = self.create_media_container(url)
                if not result["success"]:
                    return {"success": False, "error": f"Container creation failed for slide {idx}: {result.get('error')}"}
                container_ids.append(result["container_id"])

            attempt_repo.create_attempt(generation_id, container_ids)

            for idx, cid in enumerate(container_ids, start=1):
                if not self.wait_for_container(cid):
                    return {"success": False, "error": f"Slide {idx} container {cid} failed or timed out."}

            # Step 3: Create carousel container
            carousel_result = self.create_carousel(container_ids, caption=caption)
            if not carousel_result["success"]:
                return {"success": False, "error": f"Carousel container creation failed: {carousel_result.get('error')}"}

            creation_id = carousel_result["creation_id"]

            attempt_repo.transition_state(generation_id, 'CAROUSEL_CREATED', carousel_creation_id=creation_id)

            if not self.wait_for_container(creation_id):
                return {"success": False, "error": f"Carousel container {creation_id} failed or timed out."}

        # Before media_publish: Claim transition atomically
        try:
            attempt_repo.transition_state(generation_id, 'PUBLISH_REQUESTED')
        except Exception as exc:
            logger.error(f"Cannot claim PUBLISH_REQUESTED for {generation_id}: {exc}")
            return {"success": False, "error": f"Failed to claim publish lock: {exc}"}

        # Check quota limit before publishing
        quota = self.check_publishing_limit()
        if quota.get("success"):
            usage = quota.get("quota_usage", 0)
            total = quota.get("quota_total", 25)
            if usage >= total:
                logger.error(f"Quota exhausted ({usage}/{total}). Cannot publish {generation_id} right now. Transitioning to PUBLISH_RETRY_AUTHORIZED.")
                attempt_repo.transition_state(generation_id, 'PUBLISH_RETRY_AUTHORIZED')
                return {"success": False, "error": f"Publishing quota exhausted ({usage}/{total})."}

        try:
            publish_result = self.publish(creation_id)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            logger.error(f"Network error during media_publish: {exc}. Transitioning to PUBLISH_OUTCOME_UNKNOWN.")
            attempt_repo.transition_state(generation_id, 'PUBLISH_OUTCOME_UNKNOWN')
            return {"success": False, "error": f"Network error during publish: {exc}"}

        if not publish_result["success"]:
            # Depending on error, it could be ambiguous. For safety, fail closed to UNKNOWN if not specifically handled.
            error_code = publish_result.get("error_code")
            attempt_repo.transition_state(generation_id, 'PUBLISH_OUTCOME_UNKNOWN')
            return {"success": False, "error": f"Publish failed: {publish_result.get('error')}"}

        media_id = publish_result["media_id"]

        attempt_repo.transition_state(generation_id, 'PUBLISHED_MEDIA_KNOWN', media_id=media_id)

        # Step 6: Verify publication & retrieve permalink
        verify_result = self.verify_publication(media_id)
        is_verified = verify_result.get("verified", False)
        permalink = verify_result.get("permalink", "")
        if not permalink:
            permalink = self.get_permalink(media_id)

        timestamp = verify_result.get("timestamp", "")

        if is_verified:
            attempt_repo.transition_state(
                generation_id,
                'PUBLISHED_VERIFIED',
                media_id=media_id,
                permalink=permalink
            )
        else:
            logger.warning(
                f"Publication verification failed for {generation_id} with media_id {media_id}. "
                "State remains PUBLISHED_MEDIA_KNOWN."
            )

        return {
            "success": is_verified,
            "media_id": media_id,
            "permalink": permalink,
            "timestamp": timestamp,
            "verified": is_verified
        }
