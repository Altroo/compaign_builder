import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from ..models import Campaign


@pytest.mark.django_db
def test_create_daily_campaign():
    client = APIClient()
    url = reverse('campaign-list')
    payload = {
        "name": "Daily Demo",
        "schedule_type": "daily",
        "daily_emails": 2,
        "weekly_emails": 0,
        "weekly_days": [],
        "total_days": 30,
        "total_months": None,
        "ai_agent_id": "openai/gpt-oss-20b:free",
        "recipient_emails": ["test@example.com"],
    }
    response = client.post(url, payload, format='json')
    assert response.status_code == 201

    # sanity checks
    assert Campaign.objects.count() == 1
    c = Campaign.objects.first()
    assert c.daily_emails == 2
