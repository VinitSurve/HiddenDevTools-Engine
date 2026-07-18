CONTENT_REGISTRY = {
    0: { # Monday
        "niche": "github_repo",
        "sheet_name": "Github Repository",
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
    # Sunday is unconfigured / disabled for Weekly Roundup
}

class Registry:
    @staticmethod
    def get_config_for_day(weekday: int) -> dict:
        return CONTENT_REGISTRY.get(weekday, None)
