# app/models/__init__.py
# ─────────────────────────────────────────────────────────────
# Import every model module here so that SQLAlchemy registers all
# tables on Base.metadata whenever `app.models` is imported.
#
# WHY THIS MATTERS:
#   Importing `Base` alone does NOT load the model classes — a table
#   is only registered in Base.metadata when its module is imported
#   and executed. Alembic's migrations/env.py imports this package to
#   build a COMPLETE picture of the schema. If a model is missing
#   here, autogenerate will think its table is unknown and propose
#   DROPPING it. So: every model file must be imported below.
#
#   ➜ When you add a new model file, add one import line here.
# ─────────────────────────────────────────────────────────────

from app.models import banner            # noqa: F401
from app.models import community_member  # noqa: F401
from app.models import contact           # noqa: F401
from app.models import gram_awaaz        # noqa: F401
from app.models import gram_sabha        # noqa: F401
from app.models import guide             # noqa: F401
from app.models import item              # noqa: F401
from app.models import job_alert         # noqa: F401
from app.models import neta_report_card  # noqa: F401
from app.models import otp               # noqa: F401
from app.models import promise           # noqa: F401
from app.models import scheme            # noqa: F401
from app.models import unit              # noqa: F401
from app.models import user              # noqa: F401
from app.models import vendor_listing    # noqa: F401
from app.models import vikas_prastav     # noqa: F401