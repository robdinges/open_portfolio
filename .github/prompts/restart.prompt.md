---
description: "Restart the local OpenPortfolio Flask server on port 5000"
name: "Restart Flask Server"
argument-hint: "Optionally add extra diagnostics to include in the restart check"
agent: "agent"
---
Restart the local Flask server for this workspace on port 5000.

Follow these steps:
1. Detect any process listening on TCP port 5000.
2. If a process exists, stop it gracefully with SIGTERM, wait briefly, and only then force kill remaining processes.
3. Start the application from the workspace root using:
   `PYTHONPATH=src .venv/bin/python -m open_portfolio.web_app`
4. Confirm that a process is listening on port 5000 and report the result.

Requirements:
- Only affect processes bound to port 5000.
- Use the workspace virtual environment Python path shown above.
- If startup fails, include the most relevant error output and a short likely-cause analysis.
