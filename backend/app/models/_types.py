"""Shared column-type helpers for models."""
from sqlalchemy.dialects.postgresql import ENUM


def pg_enum(python_enum, name):
    """Bind to an existing Postgres enum type.

    The enum types are created by the Supabase SQL schema, so we set
    create_type=False and use the raw string values (values_callable) to
    keep member names Python-safe while matching the DB labels exactly.
    """
    return ENUM(
        python_enum,
        name=name,
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )
