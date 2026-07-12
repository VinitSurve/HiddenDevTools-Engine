"""
publish.py

Main entry point to execute the complete end-to-end production publishing pipeline.
This handles Draft discovery, rendering, Supabase upload, Instagram publishing,
and Google Drive archival.
"""

import sys

# Ensure UTF-8 output to prevent UnicodeEncodeError on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

from pipelines.developer_tools_pipeline import run

if __name__ == "__main__":
    run()
