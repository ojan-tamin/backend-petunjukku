from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

uuid_type = Uuid(as_uuid=True)
json_type = JSON().with_variant(JSONB(), "postgresql")
