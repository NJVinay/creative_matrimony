# backend/app/models/__init__.py
"""
ORM model package — import all models here so Alembic and init_db() discover them.
"""

from app.models.user import User, OTPLog  # noqa: F401
from app.models.profile import Profile, ProfilePhoto  # noqa: F401
from app.models.taxonomy import (  # noqa: F401
    RegionGroup,
    LanguageGroup,
    Religion,
    Community,
    SubCaste,
    TaxonomySynonym,
    TaxonomyModerationQueue,
)
from app.models.audit import AuditLog  # noqa: F401
from app.models.payment import SubscriptionPlan, UserSubscription, PaymentTransaction  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.match import Preference  # noqa: F401
from app.models.communication import Interest, ChatRoom, ChatParticipant, ChatMessage  # noqa: F401
from app.models.horoscope import Horoscope  # noqa: F401
from app.models.expert import (  # noqa: F401
    ExpertInquiry,
    ExpertSession,
    CareAssignment,
    CareTask,
    CareCallLog,
)
from app.models.report import Report  # noqa: F401
from app.models.safety import UserBlock, BannedPhone  # noqa: F401
