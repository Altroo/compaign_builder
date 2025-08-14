from rest_framework import viewsets
from .models import Campaign
from .serializers import CampaignSerializer
from .tasks import schedule_campaign_task
from .exceptions import TaskSchedulingException
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

import logging

logger = logging.getLogger(__name__)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    REST API for creating / managing campaigns.
    POST /campaigns/ → create a campaign and schedule the Celery job.
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer

    def perform_create(self, serializer):
        # Save the campaign first
        campaign = serializer.save()

        # Enqueue the first run of the automation
        try:
            schedule_campaign_task.apply_async(
                args=(str(campaign.id),),  # pass the UUID as string
                countdown=5,               # give the DB a moment to commit
            )
        except Exception as exc:
            logger.error(
                f"Failed to schedule campaign %s: %s",
                campaign.id,
                exc,
                exc_info=True,
            )
            raise TaskSchedulingException(
                detail=f"Could not schedule campaign {campaign.id}: {exc}"
            )


@ensure_csrf_cookie
def campaign_dashboard(request):
    """
    Renders a Semantic UI dashboard that talks to the
    ``/campaigns/`` endpoint via jQuery Ajax.
    """
    return render(request, "campaigns/dashboard.html")
