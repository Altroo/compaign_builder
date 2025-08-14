import logging
import datetime
import time
from typing import Optional, cast

from django.core.mail import EmailMessage
from openai.types.chat import ChatCompletionMessageParam
from openai import OpenAIError, OpenAI
from celery import shared_task
from django.utils import timezone
from .models import Campaign
from django.conf import settings

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helper: calculate next run time based on the campaign's schedule.
# ----------------------------------------------------------------------
def _max_days(campaign):
    """Return the maximum number of days the campaign can run."""
    if campaign.total_days:
        return campaign.total_days
    if campaign.total_months:
        return campaign.total_months * 30  # simple approx
    return None


def _next_run(campaign: Campaign, last_run: datetime.datetime) -> Optional[datetime.datetime]:
    """
    Return the datetime of the next execution based on the schedule,
    or ``None`` if the campaign has no future days.
    """
    # --------- daily ----------
    if campaign.schedule_type == Campaign.SCHEDULE_DAILY:
        # Next day, same time
        return last_run + datetime.timedelta(days=1)

    # --------- weekly ----------
    elif campaign.schedule_type == Campaign.SCHEDULE_WEEKLY:
        # Find the next day that is in ``campaign.weekly_days``.
        # ``weekday()`` returns 0=Mon … 6=Sun
        today_idx = last_run.weekday()
        days_ahead = None
        for i in range(1, 8):  # look at most a whole week ahead
            candidate = (today_idx + i) % 7
            if candidate in campaign.weekly_days:
                days_ahead = i
                break
        if days_ahead is None:
            # No days selected — stop scheduling
            return None
        return last_run + datetime.timedelta(days=days_ahead)

    # ------------------------------------------------------------------
    # Unsupported/unknown schedule
    # ------------------------------------------------------------------
    return None


def _get_prompt_variations():
    """
    Return different prompt structures to create variety in email content.
    """
    return [
        # Informational/Educational style
        {
            "tone": "informative",
            "structure": "problem-solution",
            "cta_style": "value-driven"
        },
        # Promotional style
        {
            "tone": "enthusiastic",
            "structure": "benefit-focused",
            "cta_style": "urgency"
        },
        # Personal/Story style
        {
            "tone": "conversational",
            "structure": "story-based",
            "cta_style": "curiosity"
        },
        # Professional/Direct style
        {
            "tone": "professional",
            "structure": "direct-benefits",
            "cta_style": "clear-action"
        }
    ]


def _create_enhanced_prompt(campaign, email_number, total_emails):
    """
    Create sophisticated prompts with variety and context awareness.
    """
    variations = _get_prompt_variations()
    # Use modulo to cycle through variations
    variation = variations[(email_number - 1) % len(variations)]

    # Get current day info for context
    current_day = timezone.now().strftime("%A")

    base_context = f"""You are a professional email marketing specialist writing email #{email_number} of {total_emails} 
                       for the '{campaign.name}' campaign.
        CAMPAIGN DETAILS:
        - Campaign: {campaign.name}
        - Schedule: {campaign.schedule_type} emails
        - Current email: #{email_number} of {total_emails}
        - Day: {current_day}"""

    if campaign.description:
        base_context += f"\n- Campaign context: {campaign.description}"

    # Style-specific instructions based on variation
    style_instructions = {
        "informative": "Focus on educating the reader with valuable insights or tips.",
        "enthusiastic": "Use energetic language and highlight exciting benefits or opportunities.",
        "conversational": "Write in a friendly, personal tone as if talking to a friend.",
        "professional": "Maintain a polished, business-appropriate tone with clear value propositions."
    }

    structure_instructions = {
        "problem-solution": "Start by identifying a common problem, then present your solution.",
        "benefit-focused": "Lead with the key benefits and advantages.",
        "story-based": "Include a brief, relatable story or example.",
        "direct-benefits": "Be straightforward about what the reader will gain."
    }

    cta_instructions = {
        "value-driven": "Focus the call-to-action on the value they'll receive.",
        "urgency": "Create a sense of timeliness or limited availability.",
        "curiosity": "Make them curious to learn more.",
        "clear-action": "Be direct and specific about the next step."
    }

    prompt = f"""{base_context}

        STYLE FOR THIS EMAIL:
        - Tone: {variation['tone']} ({style_instructions[variation['tone']]})
        - Structure: {variation['structure']} ({structure_instructions[variation['structure']]})
        - Call-to-action: {variation['cta_style']} ({cta_instructions[variation['cta_style']]})
        
        REQUIREMENTS:
        ✓ Write in plain text format (no HTML)
        ✓ Keep it concise: 150-300 words
        ✓ Include a compelling subject line suggestion at the top
        ✓ Make it engaging and authentic
        ✓ Include ONE clear call-to-action
        ✓ Avoid generic placeholders like [Your Name] or [Company Name]
        ✓ Make it different from previous emails in this sequence
        ✓ Consider that this is being sent on a {current_day}
        
        FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
        Subject: [Your subject line here]
        
        [Email body here]
        
        ---
        Call-to-action: [Your CTA here]"""

    return prompt


def _extract_email_parts(generated_content):
    """
    Extract subject, body, and CTA from the generated content.
    """
    lines = generated_content.split('\n')
    subject = "Marketing Update"  # default
    body_lines = []
    cta = ""

    in_body = False
    for line in lines:
        line = line.strip()
        if line.lower().startswith('subject:'):
            subject = line[8:].strip()
            in_body = True  # Start a body after a subject
        elif line.startswith('---'):
            in_body = False  # End of body, start looking for CTA
        elif line.lower().startswith('call-to-action:'):
            cta = line[15:].strip()
            in_body = False
        elif in_body and line:  # Only add to body if we're in the body section
            body_lines.append(line)

    body = '\n'.join(body_lines).strip()

    # If CTA is found, append it to the body
    if cta:
        body += f"\n\n{cta}"

    return subject, body


def _get_model_name(campaign):
    """
    Get the appropriate model name with smart defaults for OpenRouter.
    """
    if not getattr(campaign, "ai_agent_id", None):
        return "openai/gpt-3.5-turbo"

    model_id = campaign.ai_agent_id.strip()
    if not model_id:
        return "openai/gpt-3.5-turbo"

    return model_id


# ----------------------------------------------------------------------
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def schedule_campaign_task(self, campaign_id: str):
    """
    1️⃣ Load the Campaign.
    2️⃣ Send the configured number of emails using OpenRouter AI with enhanced prompts.
    3️⃣ Schedule the next run (or stop if the total duration is exceeded).
    """
    try:
        campaign: Campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found — abort")
        return

    # --------------------------------------------------------------
    # 1️⃣ How many emails to send now?
    # --------------------------------------------------------------
    if campaign.schedule_type == Campaign.SCHEDULE_DAILY:
        num_emails = campaign.daily_emails or 1
    else:  # weekly
        num_emails = campaign.weekly_emails or 1

    # --------------------------------------------------------------
    # 2️⃣ Send email(s) via OpenRouter AI with enhanced prompts
    # --------------------------------------------------------------
    model_name = _get_model_name(campaign)
    logger.info(f"[Campaign {campaign.id}] Sending {num_emails} emails using model: {model_name}")

    for i in range(num_emails):
        # ----- Build an enhanced, varied prompt -----
        prompt = _create_enhanced_prompt(campaign, i + 1, num_emails)

        # ----- Call the OpenRouter API -----
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
            messages = cast(
                list[ChatCompletionMessageParam],
                [{"role": "user", "content": prompt}]
            )

            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.8,
                max_tokens=500,
                top_p=0.9,
                presence_penalty=0.2,
                frequency_penalty=0.3,
            )

            # Extract generated text
            raw_content = completion.choices[0].message.content

            if not raw_content or raw_content.strip() == "":
                logger.warning(f"[Campaign {campaign.id}] Empty content generated, skipping email {i + 1}")
                continue

            # Parse the structured response
            subject, email_body = _extract_email_parts(raw_content)

        except OpenAIError as exc:
            logger.error(
                f"[Campaign {campaign.id}] OpenRouter request failed: {exc}"
            )
            # Re-raise to let Celery retry
            raise self.retry(exc=exc)

        # ----- Send the email -----
        try:
            email_msg = EmailMessage(
                subject=subject,  # Use AI-generated subject
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=campaign.recipient_emails or [],
            )
            email_msg.content_subtype = "plain"
            email_msg.send(fail_silently=False)

            logger.info(f"[Campaign {campaign.id}] Email {i + 1} sent successfully with subject: '{subject}'")

        except Exception as exc:
            logger.error(
                f"[Campaign {campaign.id}] Email send failed: {exc}"
            )

        # Pause between emails to be respectful to APIs and recipients
        time.sleep(1.0)  # Increased pause

    # --------------------------------------------------------------
    # 3️⃣ Check total duration and schedule next run
    # --------------------------------------------------------------
    now = timezone.now()

    # elapsed days from creation
    elapsed_days = (now - campaign.created_at).days
    # months → approx 30 days each
    max_days = _max_days(campaign)

    if max_days and elapsed_days >= max_days:
        logger.info(
            f"[Campaign {campaign.id}] total duration reached "
            f"({elapsed_days} days) — stopping."
        )
        return  # stop scheduling

    # --------------------------------------------------------------
    # Schedule next run
    # --------------------------------------------------------------
    next_run = _next_run(campaign, now)
    if next_run:
        delay = max((next_run - now).total_seconds(), 0)
        schedule_campaign_task.apply_async(
            args=(campaign_id,),
            countdown=delay,
        )
        logger.info(
            f"[Campaign {campaign.id}] Next run scheduled at {next_run} "
            f"(in {int(delay)}s)."
        )
