import logging
from features.publishing.provider import RepositoryProvider
from typing import Optional
from models.publish_job import PublishJob
from models.publish_result import PublishResult
from scheduler.publisher_interface import Publisher
from services.instagram_service import InstagramService
from features.publishing.instagram_attempt_repository import InstagramPublicationAttemptRepository
from features.publishing.repository import PublicationRepository

logger = logging.getLogger(__name__)

class InstagramGraphPublisher(Publisher):
    def __init__(self):
        try:
            self.service = InstagramService()
            self.attempt_repo = RepositoryProvider.get_instagram_attempt_repository()
            self.pub_repo = RepositoryProvider.get_publication_repository()
        except ValueError:
            self.service = None
            self.attempt_repo = None
            self.pub_repo = None

    def publish(self, job: PublishJob) -> PublishResult:
        if not self.service or not self.attempt_repo or not self.pub_repo:
            logger.error("Instagram services not fully configured. Failing closed.")
            return PublishResult(
                success=False,
                provider="Instagram",
                error_code="-1",
                error_message="InstagramGraphPublisher missing environment configuration"
            )

        # Idempotency Protection before hitting Graph API
        existing_pub = self.pub_repo.get_by_generation_id(job.generation_id)
        if existing_pub:
            logger.info(f"Idempotency hit: Generation ID {job.generation_id} already published.")
            return PublishResult(
                success=True,
                provider="Instagram",
                provider_post_id=existing_pub.get("media_id"),
                permalink=existing_pub.get("permalink"),
                published_at=existing_pub.get("published_at"),
                provider_response={"message": "Idempotent success (previously published)"},
                attempt_count=0
            )

        # Prepare payload
        image_urls = [a.public_url for a in job.artifacts if a.public_url]
        
        try:
            # Delegate to existing InstagramService
            res = self.service.publish_carousel(
                generation_id=job.generation_id,
                image_urls=image_urls,
                attempt_repo=self.attempt_repo,
                caption=job.caption
            )
            
            if res.get("success"):
                return PublishResult(
                    success=True,
                    provider="Instagram",
                    provider_post_id=res.get("media_id"),
                    permalink=res.get("permalink"),
                    published_at=res.get("timestamp"),
                    provider_response=res
                )
            else:
                return PublishResult(
                    success=False,
                    provider="Instagram",
                    error_message=res.get("error"),
                    provider_response=res
                )

        except Exception as e:
            logger.error(f"Instagram publisher exception: {e}")
            return PublishResult(
                success=False,
                provider="Instagram",
                error_code="-1",
                error_message=str(e)
            )
