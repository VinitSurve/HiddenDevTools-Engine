from pathlib import Path

# Create renderers directory
renderers = Path("renderers")
renderers.mkdir(exist_ok=True)

# Files to create
files = [
    "__init__.py",
    "github_repo.py",
    "tools_websites.py",
    "developer_tools.py",
    "prompt_library.py",
    "free_alternatives.py",
    "career_resources.py",
    "weekly_roundup.py",
]

# Create empty files
for file in files:
    (renderers / file).touch(exist_ok=True)

# Write only this line to __init__.py
(renderers / "__init__.py").write_text(
    "from .github_repo import generate_github_repo\n",
    encoding="utf-8"
)

print("✅ Baby Step 14 & 15 completed.")