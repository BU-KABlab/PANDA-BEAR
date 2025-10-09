from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 1) Import Base AND import modules that define tables so they register on Base.metadata
from panda_lib.sql_tools.models import Base
# >>> Import your model modules here (examples; adjust to your actual modules) <<<
# These imports have no side effects other than registering tables on Base.metadata.
import panda_lib.sql_tools.models  # if this file defines all tables, keep this
# If your tip models live elsewhere, import them too:
# import panda_lib.tips.models
# import panda_lib.hardware.models
# import panda_lib.experiments.models
# ...etc.

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2) Use metadata from Base; a list is fine if you truly have multiple Bases
target_metadata = [Base.metadata]

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,           # <<< important for SQLite
        compare_type=True,              # <<< pick up type changes
        compare_server_default=True,    # <<< pick up server defaults
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,           # <<< important for SQLite
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
