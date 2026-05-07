"""ORM モデルの公開インターフェース。

Base を先にインポートすることで SQLAlchemy のメタデータに全モデルが登録される。
"""

from app.models.approval import TicketApprovalOrm
from app.models.attachment import TicketAttachmentOrm
from app.models.base import Base
from app.models.comment import TicketCommentOrm
from app.models.escalation_rule import EscalationRuleOrm
from app.models.product import ProductOrm, ProductReleaseOrm
from app.models.project import ProjectOrm
from app.models.task_group import TaskGroupOrm, TicketGroupMemberOrm
from app.models.ticket import TicketDependencyOrm, TicketOrm
from app.models.user import UserOrm

__all__ = [
    "Base",
    "EscalationRuleOrm",
    "ProductOrm",
    "ProductReleaseOrm",
    "ProjectOrm",
    "TaskGroupOrm",
    "TicketApprovalOrm",
    "TicketAttachmentOrm",
    "TicketCommentOrm",
    "TicketDependencyOrm",
    "TicketGroupMemberOrm",
    "TicketOrm",
    "UserOrm",
]
