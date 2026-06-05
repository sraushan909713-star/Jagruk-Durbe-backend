# .vulture_allowlist.py
# ─────────────────────────────────────────────────────────────
# Vulture allowlist for known false positives.
#
# Vulture flags symbols it can't see being used. This file lists symbols
# that ARE used, but in ways vulture cannot detect (decorators, framework
# magic, etc). Each entry below has a one-line justification.
#
# Run vulture as:   vulture
# (pyproject.toml configures paths and min_confidence = 80)
# ─────────────────────────────────────────────────────────────

# The 4 `request: Request` parameters in auth.py routes that use
# @limiter.limit(...). slowapi inspects the function signature for a
# `request: Request` parameter to extract the client IP for rate-limiting.
# The body never references it, but removing it breaks the decorator.
request  # auth.py:74  (send_otp)
request  # auth.py:86  (register)
request  # auth.py:129 (login)
request  # auth.py:165 (reset_password)
