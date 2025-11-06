---
description: "Runs all linter tasks and fixes any issues prior to a commit"
---

Your goal is to prepare the repo to commit uncommitted changes
- Go into Debug Mode
- Run the following command: ruff check calendarbot_lite --fix && mypy calendarbot_lite && bandit -r calendarbot_lite
- If the number of errors is small - 14 or so, go ahead and fix them.
- If the number of errors is large, switch to orchestrator mode and create subtasks to tackle manageable sized sets of errors.
- There may be multiple rounds of errors - continue fixing errors until the prior task indicates no errors remain.
-You MUST continue this loop until "ruff check calendarbot_lite --fix && mypy calendarbot_lite && bandit -r calendarbot_lite" runs with ZERO errors reported
