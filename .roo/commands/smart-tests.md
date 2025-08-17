---
description: "Brief description of what this command does"
---

Your goal is to ensure that tests are updated for changes and are passing prior to checkin. 
- Switch to orchestrator mode
- Analyze python and js files in calendarbot with uncommitted changes
- Identify relevant unit tests for the uncommitted changes and run them
- For any errors found, determine if the test needs to be updated or if the implementation has a bug and take appropriate action to fix the test or the bug
- The implementation always trumps the test - never change the implementation to match the test, unless you are fixing an actual functional bug. 
- re-run the identified tests and continue to fix until all identified tests pass.