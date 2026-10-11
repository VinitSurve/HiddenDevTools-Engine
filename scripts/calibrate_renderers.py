import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from renderers.career_resources import CareerResourcesRenderer
from renderers.developer_tools_renderer import DeveloperToolsRenderer
from renderers.free_alternatives import FreeAlternativesRenderer
from renderers.github_repo import GithubRepoRenderer
from renderers.prompt_library import PromptLibraryRenderer
from renderers.tools_websites import ToolsWebsitesRenderer

renderers_map = {
    "career_resources": (CareerResourcesRenderer, {
        "resource_name": "Great Frontend Resources for Beginners",
        "website": "frontendmasters.com",
        "category": "Learning",
        "free_paid": "Free & Paid",
        "best_for_1": "Junior Developers",
        "best_for_2": "Self-Taught Devs",
        "best_for_3": "Career Transitioners",
        "why_use_it": "It offers comprehensive roadmaps and top-tier instructors for modern web development frameworks.",
        "rating": "9.5"
    }),
    "developer_tools": (DeveloperToolsRenderer, {
        "tool_name": "Visual Studio Code",
        "website": "code.visualstudio.com",
        "rating": "9.8",
        "short_description": "A lightweight but powerful source code editor which runs on your desktop and is available for Windows, macOS and Linux.",
        "best_for_1": "Web Development",
        "best_for_2": "Python & Data Science",
        "best_for_3": "Remote Development",
        "why_developers_love_it": "Massive extension ecosystem and incredibly fast performance for daily coding.",
        "category": "Code Editor",
        "license": "Open Source"
    }),
    "free_alternatives": (FreeAlternativesRenderer, {
        "alternative_name": "Photopea",
        "replaces": "Adobe Photoshop",
        "website": "photopea.com",
        "rating": "9.2",
        "why_switch": "Runs entirely in the browser, supports PSD files perfectly, and requires zero installation.",
        "best_for_1": "Quick Edits",
        "best_for_2": "Chromebook Users",
        "best_for_3": "Budget Creators",
        "category": "Design",
        "pricing": "Free"
    }),
    "github_repo": (GithubRepoRenderer, {
        "resource_name": "supabase / supabase",
        "link": "github.com/supabase",
        "rating": "9.7",
        "short_description": "The open source Firebase alternative. Build scalable and secure applications seamlessly.",
        "best_for_1": "PostgreSQL Lovers",
        "best_for_2": "Full-Stack Devs",
        "best_for_3": "Rapid Prototyping",
        "pricing": "Open Source",
        "difficulty": "Intermediate",
        "why_it_matters": "Self-hostable backend-as-a-service with built-in auth, realtime, and storage."
    }),
    "prompt_library": (PromptLibraryRenderer, {
        "prompt_title": "Code Review Assistant",
        "prompt_number": "01",
        "prompt": "Act as a senior software engineer. Review the following code snippet for performance bottlenecks, security vulnerabilities, and adherence to SOLID principles. Provide refactored code and explain the reasoning behind your changes.",
        "best_for_1": "Code quality reviews",
        "best_for_2": "Security checks",
        "best_for_3": "Learning best practices",
        "expected_output": "Line-by-line review, architectural concerns, and cleanly formatted refactored code."
    }),
    "tools_websites": (ToolsWebsitesRenderer, {
        "tool_name": "Figma",
        "website": "figma.com",
        "rating": "9.9",
        "short_description": "The collaborative interface design tool for wireframing, designing, and prototyping.",
        "best_for_1": "UI/UX Designers",
        "best_for_2": "Product Managers",
        "best_for_3": "Frontend Devs",
        "category": "Design Tool",
        "pricing": "Freemium",
        "platform": "Web/Mac/Win"
    })
}

templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
output_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "calibration"))
output_base_normal = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "normal"))

os.makedirs(output_base, exist_ok=True)
os.makedirs(output_base_normal, exist_ok=True)

for niche_id, (renderer_cls, real_data) in renderers_map.items():
    print(f"Calibrating {niche_id}...")
    try:
        renderer = renderer_cls(templates_dir)
        payloads = [real_data for _ in range(7)]
        
        # Debug version
        out_dir = os.path.join(output_base, niche_id)
        os.makedirs(out_dir, exist_ok=True)
        renderer.render(payloads, out_dir, f"calib_{niche_id}", debug_bboxes=True)
        
        # Normal version
        out_dir_normal = os.path.join(output_base_normal, niche_id)
        os.makedirs(out_dir_normal, exist_ok=True)
        renderer.render(payloads, out_dir_normal, f"normal_{niche_id}", debug_bboxes=False)
        
    except Exception as e:
        print(f"Error calibrating {niche_id}: {e}")

print("Calibration generated.")
