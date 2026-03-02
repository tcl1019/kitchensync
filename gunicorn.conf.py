# Gunicorn configuration file
# Auto-discovered by gunicorn regardless of command-line args.
# This ensures correct settings even if the Procfile/dashboard command
# doesn't include all flags.

import multiprocessing

# Use threaded workers so long API calls don't block heartbeats
worker_class = "gthread"
workers = 2
threads = 4

# 120s timeout — needed for Claude API calls + grounding fetches
timeout = 120

# Bind to PORT env var (Render sets this)
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
