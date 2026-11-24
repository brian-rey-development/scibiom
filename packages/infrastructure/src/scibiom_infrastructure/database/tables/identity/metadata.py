from sqlalchemy import MetaData

IDENTITY_SCHEMA = "identity"

# Check constraints live only in the migration, because Alembic does not compare them.
identity_metadata = MetaData(schema=IDENTITY_SCHEMA)
