import re
from typing import Optional
from settings import ENGAGEMENT_KEYWORDS

class KeywordMatcher:
    @staticmethod
    def normalize_text(text: str) -> str:
        """Lowercases, trims whitespace, and collapses multiple spaces."""
        if not text:
            return ""
        # Lowercase and trim
        text = text.lower().strip()
        # Collapse multiple spaces into one
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def match_keyword(normalized_text: str) -> Optional[str]:
        """
        Checks if the normalized text matches any alias of any configured keyword.
        Returns the root keyword if a match is found.
        """
        # We split the normalized text into words to match exact tokens
        words = set(normalized_text.split())
        
        for root_keyword, aliases in ENGAGEMENT_KEYWORDS.items():
            for alias in aliases:
                # Direct string equality or word matching
                if alias.lower() in words:
                    return root_keyword
        return None
