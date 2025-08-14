from rest_framework import status
from rest_framework.exceptions import APIException


class TaskSchedulingException(APIException):
    """
    Raised when a Celery task cannot be scheduled (e.g., the call to
    ``schedule_campaign_task.apply_async`` fails).  The ``detail`` field
    contains a human‑readable error message.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to schedule the campaign task."
    default_code = "task_scheduling_error"

    def __init__(self, detail: str | None = None):
        """
        :param detail: Optional custom error message. If omitted,
                       ``default_detail`` is used.
        """
        # Preserve the standard APIException behavior
        super().__init__(detail=detail or self.default_detail)
