from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    daily_emails = serializers.IntegerField(required=False, allow_null=True)
    weekly_emails = serializers.IntegerField(required=False, allow_null=True)
    total_days = serializers.IntegerField(required=False, allow_null=True)
    total_months = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Campaign
        fields = "__all__"

    def validate(self, data):
        """
        Run model‑level validation (model.clean()).
        Convert any Django ValidationError into a format
        expected by DRF.
        """
        try:
            # `clean()` raises `django.core.exceptions.ValidationError`
            Campaign(**data).clean()
        except DjangoValidationError as exc:
            # If the ValidationError already carries a dict,
            # pass it straight through.
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict)
            # Otherwise wrap the messages in a generic non‑field error.
            raise serializers.ValidationError(
                {"non_field_errors": exc.messages}
            )
        return data
