from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This tells Alembic about all our tables so it can auto-generate migrations
from app.database import Base
import app.models.user   # ✅ ADD: registers User model with Base
import app.models.otp    # ✅ ADD: registers OTP model with Base
import app.models.scheme
import app.models.contact
import app.models.guide
import app.models.gram_awaaz
import app.models.vikas_prastav
import app.models.gram_sabha
import app.models.neta_report_card
import app.models.vendor_listing       # ✅ singular — matches actual filename
import app.models.job_alert            # ✅ singular — matches actual filename
import app.models.community_member     # ✅ singular — matches actual filename
import app.models.banner               # ✅ singular — matches actual filename
import app.models.promise
import app.models.item   # ✅ NEW
import app.models.unit   # ✅ NEW


target_metadata = Base.metadata  # ✅ CHANGE: was None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
