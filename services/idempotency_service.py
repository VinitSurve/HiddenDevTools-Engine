import logging
import datetime
from typing import Optional, Dict, Any, List
from utils.timezone import IST

logger = logging.getLogger(__name__)

def derive_canonical_generation_id(target_date_str: str, niche: str) -> str:
    """
    Derives a stable, deterministic generation_id for a given target date and niche.
    Example: target_date_str='2026-10-23', niche='free_alternatives' -> 'GEN_20261023_FREE_ALTER'
    """
    clean_date = target_date_str.replace("-", "").strip()
    clean_niche = niche.upper().replace("-", "_").replace(" ", "_")[:10]
    return f"GEN_{clean_date}_{clean_niche}"

def _parse_ts_to_ist_date(ts_str: Optional[str]) -> Optional[str]:
    """
    Parse ISO, UTC, or local timestamp string and return IST calendar date string YYYY-MM-DD.
    If the string is naive (e.g. from Google Sheets '2026-10-23 23:28:00'), it is already
    in local IST time and its calendar date is extracted directly without false UTC shifts.
    """
    if not ts_str:
        return None
    try:
        clean_ts = ts_str.strip()
        # Check if timestamp contains explicit timezone offset or UTC indicator
        has_tz = (
            clean_ts.endswith("Z") or
            ("+" in clean_ts[10:]) or
            ("-" in clean_ts[10:] and clean_ts[10:].count("-") == 1)
        )
        if has_tz:
            if clean_ts.endswith("Z"):
                clean_ts = clean_ts[:-1] + "+00:00"
            elif len(clean_ts) >= 5 and (clean_ts[-5] in ('+', '-') and clean_ts[-3] != ':'):
                clean_ts = clean_ts[:-2] + ':' + clean_ts[-2:]
            dt = datetime.datetime.fromisoformat(clean_ts)
            return dt.astimezone(IST).strftime("%Y-%m-%d")
        else:
            # Naive timestamp, already recorded in IST
            if len(clean_ts) >= 10 and clean_ts[4] == '-' and clean_ts[7] == '-':
                return clean_ts[:10]
            dt = datetime.datetime.fromisoformat(clean_ts)
            return dt.strftime("%Y-%m-%d")
    except Exception:
        if len(ts_str) >= 10 and ts_str[4] == '-' and ts_str[7] == '-':
            return ts_str[:10]
        return None

def check_already_published(
    target_date_str: str,
    niche: str,
    sheet_name: Optional[str] = None,
    pub_repo=None,
    attempt_repo=None,
    worksheet=None,
    instagram_attempt_repo=None,
    upload_attempt_repo=None
) -> Dict[str, Any]:
    """
    Durable pre-publish idempotency check.
    Queries Supabase/SQLite publication repository, attempt repository, and Google Sheets
    to determine whether content for the target date and niche was already published.

    Fails closed if the authoritative publication repository encounters a database/network error
    and no other verified source can confirm publication state.
    """
    from utils.timezone import get_scheduled_publishing_target

    canonical_gen_id = derive_canonical_generation_id(target_date_str, niche)
    check_errors: List[str] = []

    # 1. Check Publication Repository
    if pub_repo:
        try:
            # Check by deterministic canonical ID
            canonical_rec = pub_repo.get_by_generation_id(canonical_gen_id)
            if canonical_rec and canonical_rec.get("media_id"):
                media_id = canonical_rec.get("media_id")
                if media_id not in ("UNKNOWN", "SIMULATED_MEDIA_ID"):
                    logger.info(f"Idempotency hit by canonical generation_id {canonical_gen_id}")
                    return {
                        "is_published": True,
                        "generation_id": canonical_gen_id,
                        "media_id": media_id,
                        "permalink": canonical_rec.get("permalink", ""),
                        "published_at": canonical_rec.get("published_at", ""),
                        "sheet_sync_state": canonical_rec.get("sheet_sync_state", "PENDING"),
                        "source": "pub_repo_canonical",
                        "needs_sheet_sync": canonical_rec.get("sheet_sync_state") != "SUCCESS",
                        "has_error": False
                    }

            # Check recent publications for match on target date window or slot
            recent = pub_repo.get_recent_publications(limit=15)
            for rec in recent:
                media_id = rec.get("media_id", "")
                if media_id in ("UNKNOWN", "SIMULATED_MEDIA_ID", ""):
                    continue
                pub_ts = rec.get("published_at")
                rec_date_ist = _parse_ts_to_ist_date(pub_ts)

                # Check slot match if rollover
                slot_match = False
                try:
                    if pub_ts:
                        clean_pub = pub_ts.strip()
                        if clean_pub.endswith("Z"):
                            clean_pub = clean_pub[:-1] + "+00:00"
                        pub_dt = datetime.datetime.fromisoformat(clean_pub)
                        pub_slot_target = get_scheduled_publishing_target(now_ist=pub_dt)["target_date_str"]
                        slot_match = (pub_slot_target == target_date_str)
                except Exception:
                    pass

                # If published on target date or within target date publishing slot
                if rec_date_ist == target_date_str or slot_match:
                    logger.info(f"Idempotency hit by recent publication match: {rec.get('generation_id')} (date={rec_date_ist}, slot_match={slot_match})")
                    return {
                        "is_published": True,
                        "generation_id": rec.get("generation_id", canonical_gen_id),
                        "media_id": media_id,
                        "permalink": rec.get("permalink", ""),
                        "published_at": rec.get("published_at", ""),
                        "sheet_sync_state": rec.get("sheet_sync_state", "PENDING"),
                        "source": "pub_repo_recent_date",
                        "needs_sheet_sync": rec.get("sheet_sync_state") != "SUCCESS",
                        "has_error": False
                    }
        except Exception as e:
            logger.error(f"Error querying publication repository for idempotency check: {e}")
            check_errors.append(f"pub_repo: {e}")

    # 2. Check Attempt Repositories (Instagram Publication and Upload Attempts)
    # Check Instagram publication attempt repo first (if provided or passed as attempt_repo)
    ig_repo = instagram_attempt_repo
    if ig_repo is None and attempt_repo is not None:
        if hasattr(attempt_repo, "transition_state"):
            ig_repo = attempt_repo
        elif not hasattr(attempt_repo, "record_attempt") and not hasattr(attempt_repo, "get_all_attempts"):
            ig_repo = attempt_repo

    if ig_repo:
        try:
            attempt = ig_repo.get_attempt(canonical_gen_id)
            if attempt and attempt.get("publish_state") in ("PUBLISHED_VERIFIED", "PUBLISHED_MEDIA_KNOWN"):
                media_id = attempt.get("media_id")
                if media_id and media_id not in ("UNKNOWN", "SIMULATED_MEDIA_ID"):
                    logger.info(f"Idempotency hit by attempt repository state {attempt.get('publish_state')}")
                    return {
                        "is_published": True,
                        "generation_id": canonical_gen_id,
                        "media_id": media_id,
                        "permalink": attempt.get("permalink", ""),
                        "published_at": attempt.get("updated_at", ""),
                        "sheet_sync_state": "PENDING",
                        "source": "instagram_attempt_repo",
                        "needs_sheet_sync": True,
                        "has_error": False
                    }
        except Exception as e:
            logger.error(f"Error querying Instagram attempt repository for idempotency check: {e}")
            check_errors.append(f"instagram_attempt_repo: {e}")

    # Check Upload Attempt Repository safely for generation attempts
    up_repo = upload_attempt_repo
    if up_repo is None and attempt_repo is not None and attempt_repo is not ig_repo:
        up_repo = attempt_repo
    elif up_repo is None and attempt_repo is not None and (hasattr(attempt_repo, "record_attempt") or hasattr(attempt_repo, "get_all_attempts")):
        up_repo = attempt_repo

    if up_repo:
        try:
            # Query attempts for the generation safely with optional slide_number
            _ = up_repo.get_attempt(canonical_gen_id)
        except Exception as e:
            logger.error(f"Error querying upload attempt repository for idempotency check: {e}")
            check_errors.append(f"upload_attempt_repo: {e}")

    # 3. Check Google Sheets row state
    if sheet_name:
        try:
            ws = worksheet
            if ws is None:
                try:
                    from sheet_api import open_sheet
                    ws = open_sheet(sheet_name)
                except Exception as e:
                    ws = None
                    check_errors.append(f"sheet_open: {e}")
            if ws and hasattr(ws, "get_all_records"):
                records = ws.get_all_records()
                for r in records:
                    status = str(r.get("Status", "")).strip().lower()
                    post = str(r.get("Post", "")).strip()
                    gen_id = str(r.get("Generation ID", "")).strip()
                    gen_at_date = _parse_ts_to_ist_date(str(r.get("Generated At", "")))
                    pub_at_date = _parse_ts_to_ist_date(str(r.get("Published At", "")))

                    if status == "published" and "instagram.com" in post:
                        if gen_id == canonical_gen_id or gen_at_date == target_date_str or pub_at_date == target_date_str:
                            logger.info(f"Idempotency hit by Google Sheets record in {sheet_name} (ID: {r.get('ID')}, GenID: {gen_id})")
                            return {
                                "is_published": True,
                                "generation_id": gen_id or canonical_gen_id,
                                "media_id": "SHEET_VERIFIED",
                                "permalink": post,
                                "published_at": r.get("Published At") or r.get("Generated At") or "",
                                "sheet_sync_state": "SUCCESS",
                                "source": "google_sheets",
                                "needs_sheet_sync": False,
                                "has_error": False
                            }
        except Exception as e:
            logger.error(f"Error querying Google Sheets for idempotency check: {e}")
            check_errors.append(f"sheets_query: {e}")

    # Fail closed if authoritative repository check failed and no source confirmed publication
    if check_errors:
        err_msg = "; ".join(check_errors)
        logger.error(f"Idempotency check encountered backend errors: {err_msg}")
        return {
            "is_published": False,
            "has_error": True,
            "error": err_msg,
            "generation_id": canonical_gen_id,
            "media_id": None,
            "permalink": None,
            "published_at": None,
            "sheet_sync_state": None,
            "source": None,
            "needs_sheet_sync": False
        }

    return {
        "is_published": False,
        "has_error": False,
        "error": None,
        "generation_id": canonical_gen_id,
        "media_id": None,
        "permalink": None,
        "published_at": None,
        "sheet_sync_state": None,
        "source": None,
        "needs_sheet_sync": False
    }
