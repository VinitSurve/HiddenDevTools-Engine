import logging
from typing import Optional
from features.publishing.instagram_attempt_repository import InstagramPublicationAttemptRepository
from features.publishing.repository import PublicationRepository

logger = logging.getLogger(__name__)

class PublicationReconciliationConflictError(Exception):
    pass

class ManualPublicationReconciliationService:
    def __init__(self, 
                 attempt_repo: InstagramPublicationAttemptRepository,
                 publication_repo: PublicationRepository):
        self.attempt_repo = attempt_repo
        self.publication_repo = publication_repo

    def verify_published(self, 
                         generation_id: str, 
                         verified_permalink: str, 
                         verified_published_at: str, 
                         verified_media_id: Optional[str] = None) -> None:
        if not generation_id or not generation_id.strip():
            raise ValueError("generation_id is required")
        if not verified_permalink or not verified_permalink.strip():
            raise ValueError("verified_permalink is required")
        if not verified_published_at or not verified_published_at.strip():
            raise ValueError("verified_published_at is required")
            
        generation_id = generation_id.strip()
        verified_permalink = verified_permalink.strip()
        verified_published_at = verified_published_at.strip()
        if verified_media_id is not None:
            verified_media_id = verified_media_id.strip()

        attempt = self.attempt_repo.get_attempt(generation_id)
        if not attempt:
            raise ValueError(f"No instagram publication attempt found for {generation_id}")

        state = attempt['publish_state']
        if state not in ('PUBLISHED_MEDIA_KNOWN', 'PUBLISH_OUTCOME_UNKNOWN'):
            raise ValueError(f"Cannot manually reconcile from state {state}")

        persisted_media_id = attempt.get('media_id')
        final_media_id = None

        if state == 'PUBLISHED_MEDIA_KNOWN':
            if not persisted_media_id:
                # This should be impossible due to repository constraints, but defensively check
                raise ValueError("PUBLISHED_MEDIA_KNOWN attempt is missing its media_id")
                
            if verified_media_id is not None:
                if verified_media_id != persisted_media_id:
                    raise PublicationReconciliationConflictError(
                        f"Supplied media_id {verified_media_id} differs from immutable persisted media_id {persisted_media_id}"
                    )
            
            final_media_id = persisted_media_id

        elif state == 'PUBLISH_OUTCOME_UNKNOWN':
            if not verified_media_id:
                raise ValueError("verified_media_id is mandatory for PUBLISH_OUTCOME_UNKNOWN")
            
            if persisted_media_id:
                if verified_media_id != persisted_media_id:
                    raise PublicationReconciliationConflictError(
                        f"Supplied media_id {verified_media_id} differs from unexpectedly present persisted media_id {persisted_media_id}"
                    )
            
            final_media_id = verified_media_id

        # Actually record the publication canonical record
        # Note: If this fails, the exception propagates and the attempt state is NOT mutated.
        logger.info(f"Manual reconciliation VERIFIED_PUBLISHED for {generation_id} with media_id {final_media_id}")
        self.publication_repo.record_publication(
            generation_id=generation_id,
            media_id=final_media_id,
            permalink=verified_permalink,
            canonical_time=verified_published_at
        )

        # Transition the attempt state
        self.attempt_repo.transition_state(
            generation_id, 
            'PUBLISHED_VERIFIED', 
            media_id=final_media_id, 
            permalink=verified_permalink
        )

    def verify_not_published(self, generation_id: str) -> None:
        if not generation_id or not generation_id.strip():
            raise ValueError("generation_id is required")
        
        generation_id = generation_id.strip()
        
        attempt = self.attempt_repo.get_attempt(generation_id)
        if not attempt:
            raise ValueError(f"No instagram publication attempt found for {generation_id}")

        state = attempt['publish_state']
        if state != 'PUBLISH_OUTCOME_UNKNOWN':
            raise ValueError(f"VERIFIED_NOT_PUBLISHED requires PUBLISH_OUTCOME_UNKNOWN, got {state}")

        logger.info(f"Manual reconciliation VERIFIED_NOT_PUBLISHED for {generation_id}. Authorizing retry.")
        self.attempt_repo.transition_state(generation_id, 'PUBLISH_RETRY_AUTHORIZED')
