from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, campaign_dashboard

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
    path("", campaign_dashboard, name="dashboard"),
]
