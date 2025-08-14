from django.contrib import admin
from .models import Campaign


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "schedule_type",
        "daily_emails",
        "weekly_emails",
        "total_days",
        "total_months",
        "created_at",
        "updated_at",
    )
    list_filter = ("schedule_type", "created_at")
    search_fields = ("name", "description", "ai_agent_id")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
