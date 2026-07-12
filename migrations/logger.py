"""
logger.py

Simple logging utilities for the Migration Framework.
"""


def title(text):

    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def success(text):

    print(f"✓ {text}")


def error(text):

    print(f"✗ {text}")


def info(text):

    print(f"• {text}")