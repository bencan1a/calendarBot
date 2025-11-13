#!/usr/bin/env python3
"""
Main entry point for VSCode debugging compatibility.

This file exists to support VSCode's Python debugger which expects a main.py file.
The actual application entry point is defined in calendarbot_lite.__main__:main
and can be run using: python -m calendarbot_lite
"""

if __name__ == "__main__":
    from calendarbot_lite.__main__ import main

    main()
