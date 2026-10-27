import os
import sys
import logging
from config.app_config import config
from features.publishing.migrations_runner import run_publishing_migrations, validate_publishing_migrations
from settings import FONTS_DIR, TEMPLATES, OUTPUT_DIR

logger = logging.getLogger(__name__)

class StartupValidationError(Exception):
    pass

def validate_startup(read_only: bool = False):
    logger.info(f"Running startup validation (read_only={read_only})...")
    
    # 1. Check directories
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logger.info(f"Created output directory at {OUTPUT_DIR}")
        except Exception as e:
            raise StartupValidationError(f"Could not create output directory {OUTPUT_DIR}: {e}")
            
    if not os.access(OUTPUT_DIR, os.W_OK):
        raise StartupValidationError(f"Output directory {OUTPUT_DIR} is not writable.")
        
    # 2. Check templates
    for name, path in TEMPLATES.items():
        if not os.path.exists(path):
            raise StartupValidationError(f"Required template '{name}' not found at {path}")
            
    # 3. Check fonts
    if not os.path.exists(FONTS_DIR):
        raise StartupValidationError(f"Fonts directory not found at {FONTS_DIR}")
        
    # 4. Check configuration
    if not config.services.instagram.access_token:
        raise StartupValidationError("INSTAGRAM_ACCESS_TOKEN is missing")
    if not config.services.supabase.url or not config.services.supabase.service_role_key:
        raise StartupValidationError("Supabase configuration is missing (URL or SERVICE_ROLE_KEY)")
    if not os.path.exists(config.services.google_sheets.service_account_file):
        raise StartupValidationError(f"Google Sheets service account file not found at {config.services.google_sheets.service_account_file}")
        
    # 5. Check database migrations
    try:
        if read_only:
            validate_publishing_migrations()
            logger.info("Database migrations verified (read-only mode).")
        else:
            run_publishing_migrations()
            logger.info("Database migrations up-to-date.")
    except Exception as e:
        raise StartupValidationError(f"Failed to check database migrations: {e}")
        
    logger.info("Startup validation passed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        validate_startup()
        sys.exit(0)
    except StartupValidationError as e:
        logger.error(f"Startup Validation Failed: {e}")
        sys.exit(1)
