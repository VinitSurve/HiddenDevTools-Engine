# ==========================================================
# Template Registry
# ==========================================================

TEMPLATES = {

    "github_repo": {
        "config": "templates/github_repo.py"
    },

    "tools_websites": {
        "config": "templates/tools_websites.py"
    },

    "developer_tools": {
        "config": "templates/developer_tools.py"
    },

    "prompt_library": {
        "config": "templates/prompt_library.py"
    },

    "free_alternatives": {
        "config": "templates/free_alternatives.py"
    },

    "career_resources": {
        "config": "templates/career_resources.py"
    },

    "weekly_roundup": {
        "config": "templates/weekly_roundup.py"
    }

}

def get_template(template_name):

    return TEMPLATES.get(template_name)