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
        "Resource Name": "Great Frontend Resources for Beginners",
        "Website": "frontendmasters.com",
        "Category": "Learning",
        "Free/Paid": "Free & Paid",
        "Best For 1": "Junior Developers",
        "Best For 2": "Self-Taught Devs",
        "Best For 3": "Career Transitioners",
        "Why Use It": "It offers comprehensive roadmaps and top-tier instructors for modern web development frameworks.",
        "Rating": "9.5"
    }),
    "developer_tools": (DeveloperToolsRenderer, {
        "Tool Name": "Visual Studio Code",
        "Website": "code.visualstudio.com",
        "Rating": "9.8",
        "Short Description": "A lightweight but powerful source code editor which runs on your desktop and is available for Windows, macOS and Linux.",
        "Best for 1": "Web Development",
        "Best for 2": "Python & Data Science",
        "Best for 3": "Remote Development",
        "Why Developers Love it": "Massive extension ecosystem and incredibly fast performance for daily coding.",
        "Category": "Code Editor",
        "License": "Open Source"
    }),
    "free_alternatives": (FreeAlternativesRenderer, {
        "Alternative Name": "Photopea",
        "Replaces": "Adobe Photoshop",
        "Website": "photopea.com",
        "Rating": "9.2",
        "Why Switch": "Runs entirely in the browser, supports PSD files perfectly, and requires zero installation.",
        "Best For 1": "Quick Edits",
        "Best For 2": "Chromebook Users",
        "Best For 3": "Budget Creators",
        "Category": "Design",
        "Pricing": "Free"
    }),
    "github_repo": (GithubRepoRenderer, {
        "Resource Name": "supabase / supabase",
        "Link": "github.com/supabase",
        "Rating": "9.7",
        "Short Description": "The open source Firebase alternative. Build scalable and secure applications seamlessly.",
        "Best for 1": "PostgreSQL Lovers",
        "Best for 2": "Full-Stack Devs",
        "Best for 3": "Rapid Prototyping",
        "Pricing": "Open Source",
        "Difficulty": "Intermediate",
        "Why it Matters": "Self-hostable backend-as-a-service with built-in auth, realtime, and storage."
    }),
    "prompt_library": (PromptLibraryRenderer, {
        "Prompt Title": "Code Review Assistant",
        "Prompt Number": "01",
        "Prompt": "Act as a senior software engineer. Review the following code snippet for performance bottlenecks, security vulnerabilities, and adherence to SOLID principles. Provide refactored code and explain the reasoning behind your changes.",
        "Best for 1": "Code quality reviews",
        "Best for 2": "Security checks",
        "Best for 3": "Learning best practices",
        "Expected Output": "Line-by-line review, architectural concerns, and cleanly formatted refactored code."
    }),
    "tools_websites": (ToolsWebsitesRenderer, {
        "Tool Name": "Figma",
        "Website": "figma.com",
        "Rating": "9.9",
        "Short Description": "The collaborative interface design tool for wireframing, designing, and prototyping.",
        "Best for 1": "UI/UX Designers",
        "Best for 2": "Product Managers",
        "Best for 3": "Frontend Devs",
        "Category": "Design Tool",
        "Pricing": "Freemium",
        "Platform": "Web/Mac/Win"
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
