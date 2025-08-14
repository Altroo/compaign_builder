from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from django.core.exceptions import ValidationError


class Campaign(models.Model):
    """
    A campaign is a container for schedule & AI‑agent configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # ---------- schedule ----------
    SCHEDULE_DAILY = "daily"
    SCHEDULE_WEEKLY = "weekly"
    SCHEDULE_CHOICES = [
        (SCHEDULE_DAILY, "Daily"),
        (SCHEDULE_WEEKLY, "Weekly"),
    ]

    schedule_type = models.CharField(max_length=6, choices=SCHEDULE_CHOICES)
    daily_emails = models.PositiveIntegerField(default=2)   # daily schedule
    weekly_emails = models.PositiveIntegerField(
        default=5,
        null=True,
        blank=True,
    )  # per selected day (used only for weekly schedules)

    # weekly days (0=Mon … 6=Sun)
    weekly_days = ArrayField(
        base_field=models.PositiveSmallIntegerField(),
        size=7,
        blank=True,
        default=list,
        help_text="List of weekdays (0=Mon … 6=Sun) on which to send emails",
    )

    # ---------- total duration ----------
    # Both are optional; if both are supplied we **won’t** raise an error.
    total_days = models.PositiveIntegerField(null=True, blank=True)
    total_months = models.PositiveIntegerField(null=True, blank=True)

    # ---------- AI Agent ----------
    ai_agent_id = models.CharField(max_length=255, blank=True)

    recipient_emails = ArrayField(
        base_field=models.EmailField(),
        size=10,
        blank=True,
        default=list,
        help_text="E‑mail addresses that will receive the campaign’s messages",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns"

    def __str__(self):
        return self.name

    # ------------------------------------------------------------------
    # Model‑level validation
    # ------------------------------------------------------------------
    def clean(self):
        """
        Validate:
        * At least one recipient email.
        * When a schedule is weekly, `weekly_days` must not be empty.
        * Email‑count fields must be > 0.
        """
        # 1️⃣ recipients
        if not self.recipient_emails:
            raise ValidationError(
                "At least one recipient e‑mail address must be set."
            )

        # 2️⃣ total_days / total_months are now **fully optional**.
        #    If you still want to enforce “only one”, uncomment the block
        #    below. For now we let both be set or both be blank.
        #
        # if self.total_days and self.total_months:
        #     raise ValidationError(
        #         "Only one of `total_days` or `total_months` may be set."
        #     )

        # 3️⃣ schedule‑specific checks
        if self.schedule_type == self.SCHEDULE_DAILY:
            if self.daily_emails <= 0:
                raise ValidationError(
                    "`daily_emails` must be > 0 for a daily schedule."
                )
        elif self.schedule_type == self.SCHEDULE_WEEKLY:
            if not self.weekly_days:
                raise ValidationError(
                    "`weekly_days` cannot be empty for a weekly schedule."
                )
            # weekly_emails may be NULL for a daily campaign; enforce
            # positivity only for weekly schedules
            if not self.weekly_emails or self.weekly_emails <= 0:
                raise ValidationError(
                    "`weekly_emails` must be > 0 for a weekly schedule."
                )
        else:
            raise ValidationError(f"Invalid schedule type: {self.schedule_type}")
