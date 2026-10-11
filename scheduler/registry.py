CONTENT_REGISTRY = {
    0: { # Monday
        "niche": "github_repo",
        "sheet_name": "Github Repos",
    },
    1: { # Tuesday
        "niche": "tools_websites",
        "sheet_name": "Tools & Websites",
    },
    2: { # Wednesday
        "niche": "developer_tools",
        "sheet_name": "Developer Tools",
    },
    3: { # Thursday
        "niche": "prompt_library",
        "sheet_name": "Prompt Library",
    },
    4: { # Friday
        "niche": "free_alternatives",
        "sheet_name": "Free Alternatives",
    },
    5: { # Saturday
        "niche": "career_resources",
        "sheet_name": "Career Resources",
    },
    6: { # Sunday
        "niche": "weekly_roundup",
        "sheet_name": "Weekly Roundup",
    },
}

class Registry:
    @staticmethod
    def get_config_for_day(weekday: int) -> dict:
        if weekday not in CONTENT_REGISTRY:
            raise ValueError(f"Unknown weekday {weekday}. Must be 0-6.")
        return CONTENT_REGISTRY[weekday]

    @classmethod
    def validate(cls):
        # 1. exactly 7 mappings
        if len(CONTENT_REGISTRY) != 7:
            raise RuntimeError(f"Registry must have exactly 7 mappings, found {len(CONTENT_REGISTRY)}")
        
        # 2. no unmapped weekday
        for i in range(7):
            if i not in CONTENT_REGISTRY:
                raise RuntimeError(f"Registry is missing mapping for weekday {i}")
                
        # 3. no duplicate mappings (niche and sheet_name combo)
        seen = set()
        for i in range(7):
            config = CONTENT_REGISTRY[i]
            identifier = f"{config['niche']}-{config['sheet_name']}"
            if identifier in seen:
                raise RuntimeError(f"Duplicate registry mapping found: {identifier}")
            seen.add(identifier)

# Validate at import time
Registry.validate()
