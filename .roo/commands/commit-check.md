---
description: "Runs all linter tasks and fixes any issues prior to a commit"
---

Your goal is to prepare the repo to commit uncommitted changes
- go into orchestrator mode
- Stage all changes
- now begin a repeated set of sub tasks. each sub task will
    - Run the pre-commit command
    - Identify all errors detected and correct them. 
        - you must ONLY fix errors in the calendarbot directory, not the tests directory
        - Be thoughtful about which errors should actually be fixed and which should simply be overriden. Only change the code when you perceive a meaningful benefit from doing so.
        - Make local overrides - do not change the global overrides
    - once the initial errors are fixed, run pre-commit again
    - make a simple report indicating the changes made and whether any errors remain from the second pre-commit call
    - use the attempt_completion tool to return
- There will be multiple rounds of errors - create a new subtask to continue fixing errors until the prior task indicates no errors remain. You MUST continue this loop until pre-commit runs with ZERO errors reported
- Once you've confirmed pre-commit runs with no errors, unstage the changes and end the task 
