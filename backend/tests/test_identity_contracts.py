from app.models.base import Base
from app.modules.auth.models.identity import User


def test_user_email_is_required_in_metadata() -> None:
    assert Base.metadata.tables["users"].c.email.nullable is False
    assert User.__table__.c.email.nullable is False
