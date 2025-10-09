# from logging.config import fileConfig
# from sqlalchemy import engine_from_config, pool
# from alembic import context
# from sqlmodel import SQLModel
# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Import your models so Alembic knows what to track
# from models import media_interaction  # adjust import path to your project
# from database import engine  # optional if you have a helper

# # this is the Alembic Config object, which provides access to the .ini file
# config = context.config

# # Interpret the config file for Python logging
# fileConfig(config.config_file_name)

# # Use .env DATABASE_URL dynamically
# database_url = os.getenv("DATABASE_URL")
# if database_url:
#     config.set_main_option("sqlalchemy.url", database_url)

# target_metadata = SQLModel.metadata


# def run_migrations_offline():
#     """Run migrations in 'offline' mode."""
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )
#     with context.begin_transaction():
#         context.run_migrations()


# def run_migrations_online():
#     """Run migrations in 'online' mode."""
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section),
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection,
#             target_metadata=target_metadata,
#         )

#         with context.begin_transaction():
#             context.run_migrations()


# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()



# ##########################################
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
from alembic import context
from core.config import settings
from database import engine
from models import *

config = context.config
fileConfig(config.config_file_name)
target_metadata = SQLModel.metadata

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()

