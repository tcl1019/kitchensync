# Gunicorn configuration file
# Auto-discovered by gunicorn regardless of command-line args.
# This ensures correct worker class and timeout even when the
# Render dashboard start command doesn't include all flags.
#
# NOTE: Do NOT set 'bind' here — the dashboard command already
# sets --bind, and duplicating it causes conflicts.

# Use threaded workers so long API calls don't block heartbeats
worker_class = "gthread"
threads = 4

# 120s timeout — needed for Claude API calls + grounding fetches
timeout = 120
