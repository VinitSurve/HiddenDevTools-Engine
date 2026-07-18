import datetime

# Monday=0, Sunday=6
DAY_TO_NICHE_MAP = {
    0: "github_repo",
    1: "tools_websites",
    2: "developer_tools",
    3: "prompt_library",
    4: "free_alternatives",
    5: "career_resources",
    6: None # Sunday (Weekly Roundup excluded)
}

class ContentSelector:
    @staticmethod
    def get_todays_niche(override_day: int = None) -> str:
        \"\"\"
        Determines the niche to publish based on the day of the week.
        Returns the niche string, or None if no post is scheduled for today.
        \"\"\"
        day = override_day if override_day is not None else datetime.datetime.now().weekday()
        return DAY_TO_NICHE_MAP.get(day)
