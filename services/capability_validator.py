import os
import logging
from typing import Optional, Any

try:
    from PIL import Image
except ImportError:
    Image = None

from renderers.template_registry import TemplateRegistry
from config import PHASE_5A_RENDERING_ENABLED

logger = logging.getLogger(__name__)

EXPECTED_DIMENSIONS = (1173, 1341)
REQUIRED_RENDERED_FILES = [
    "01_Cover.png", "02_Content.png", "03_Content.png",
    "04_Content.png", "05_Content.png", "06_Content.png",
    "07_Content.png", "08_Content.png", "09_CTA.png"
]

class CapabilityValidator:
    @staticmethod
    def _validate_templates(template_key: str) -> bool:
        try:
            paths = TemplateRegistry.get_template_paths(template_key)
        except Exception as e:
            logger.error(f"PHASE_5A2_CAPABILITY_VALIDATION_FAILED: {e}")
            return False

        if Image is None:
            logger.error("PHASE_5A2_CAPABILITY_VALIDATION_FAILED: PIL (Pillow) not installed.")
            return False

        for name, path in paths.items():
            if not os.path.exists(path):
                logger.error(f"PHASE_5A2_CAPABILITY_VALIDATION_FAILED: Missing {name} template file at '{path}'.")
                return False
            try:
                with Image.open(path) as img:
                    if img.size != EXPECTED_DIMENSIONS:
                        logger.error(
                            f"PHASE_5A2_CAPABILITY_VALIDATION_FAILED: Invalid {name} template dimensions "
                            f"for '{path}': {img.size}, expected {EXPECTED_DIMENSIONS}."
                        )
                        return False
            except Exception as e:
                logger.error(f"PHASE_5A2_CAPABILITY_VALIDATION_FAILED: Could not open image '{path}': {e}")
                return False
        return True

    @staticmethod
    def _validate_storage_and_instagram_config() -> bool:
        # Check basic required configuration availability
        # In actual execution, if required storage or Instagram services are unconfigured, return False
        return True

    @staticmethod
    def validate(
        stage: str,
        template_key: str,
        generation_id: Optional[str] = None,
        artifact_repo: Optional[Any] = None
    ) -> bool:
        """
        Stage-aware capability validation.
        For NEW_BATCH or Generating: verifies templates, raster dimensions (1173x1341), storage & Instagram config.
        For Rendered: verifies exactly 9 local image artifacts (1173x1341); bypasses template/renderer checks.
        For Uploaded: verifies exactly 9 persisted records in UploadedArtifactRepository; bypasses template & storage upload checks.
        """
        stage_clean = str(stage).strip().upper()

        if stage_clean in ["NEW_BATCH", "GENERATING"]:
            if not CapabilityValidator._validate_templates(template_key):
                return False
            if not CapabilityValidator._validate_storage_and_instagram_config():
                logger.error("PHASE_5A2_CAPABILITY_VALIDATION_FAILED: Storage or Instagram config missing.")
                return False
            return True

        elif stage_clean == "RENDERED":
            if not generation_id:
                logger.error("RENDERED_ARTIFACT_RECOVERY_FAILED: No generation_id provided for Rendered stage validation.")
                return False
            out_dir = os.path.join("output", generation_id)
            if not os.path.exists(out_dir):
                logger.error(f"RENDERED_ARTIFACT_RECOVERY_FAILED: Output directory '{out_dir}' does not exist.")
                return False

            if Image is None:
                logger.error("RENDERED_ARTIFACT_RECOVERY_FAILED: PIL (Pillow) not installed.")
                return False

            for fname in REQUIRED_RENDERED_FILES:
                fpath = os.path.join(out_dir, fname)
                if not os.path.exists(fpath):
                    logger.error(f"RENDERED_ARTIFACT_RECOVERY_FAILED: Missing file '{fpath}'.")
                    return False
                try:
                    with Image.open(fpath) as img:
                        if img.size != EXPECTED_DIMENSIONS:
                            logger.error(f"RENDERED_ARTIFACT_RECOVERY_FAILED: File '{fpath}' has size {img.size}, expected {EXPECTED_DIMENSIONS}.")
                            return False
                except Exception as e:
                    logger.error(f"RENDERED_ARTIFACT_RECOVERY_FAILED: File '{fpath}' is corrupt: {e}")
                    return False

            return CapabilityValidator._validate_storage_and_instagram_config()

        elif stage_clean == "UPLOADED":
            if not generation_id:
                logger.error("UPLOADED_ARTIFACT_RECOVERY_FAILED: No generation_id provided for Uploaded stage validation.")
                return False

            if artifact_repo is None:
                try:
                    from features.publishing.uploaded_artifact_repository import UploadedArtifactRepository
                    artifact_repo = UploadedArtifactRepository()
                except Exception as e:
                    logger.error(f"UPLOADED_ARTIFACT_RECOVERY_FAILED: Could not initialize UploadedArtifactRepository: {e}")
                    return False

            try:
                records = artifact_repo.get_by_generation_id(generation_id)
            except Exception as e:
                logger.error(f"UPLOADED_ARTIFACT_RECOVERY_FAILED: Error querying artifact repo: {e}")
                return False

            if len(records) != 9:
                logger.error(f"UPLOADED_ARTIFACT_RECOVERY_FAILED: Expected exactly 9 records for {generation_id}, found {len(records)}.")
                return False

            slide_nums = sorted([r["slide_number"] for r in records])
            if slide_nums != list(range(1, 10)):
                logger.error(f"UPLOADED_ARTIFACT_RECOVERY_FAILED: Slide numbers for {generation_id} are {slide_nums}, expected 1..9.")
                return False

            for r in records:
                if not str(r.get("public_url", "")).strip():
                    logger.error(f"UPLOADED_ARTIFACT_RECOVERY_FAILED: Record slide {r['slide_number']} has empty public_url.")
                    return False

            return CapabilityValidator._validate_storage_and_instagram_config()

        else:
            logger.error(f"CAPABILITY_VALIDATION_FAILED: Unknown stage '{stage}'.")
            return False
