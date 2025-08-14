# Campaign Builder

An intelligent, AI-powered email marketing automation platform built with Django and Celery. This system allows users to create and manage email campaigns with sophisticated AI-generated content that adapts and evolves over time.

## Overview

Campaign Builder is a full-stack web application that combines the power of AI language models with robust scheduling capabilities to deliver personalized, context-aware email marketing campaigns. The system uses OpenRouter AI to generate varied, engaging content while maintaining campaign consistency and brand voice.

## Key Features

- **AI-Powered Content Generation**: Uses OpenRouter API with multiple AI models to create dynamic, varied email content
- **Flexible Scheduling**: Supports both daily and weekly campaign schedules with customizable frequency
- **Content Variation**: Implements sophisticated prompt engineering to ensure each email feels unique and engaging
- **Campaign Management**: Web-based dashboard for creating, monitoring, and managing campaigns
- **Scalable Architecture**: Built with Django, Celery, Redis, and PostgreSQL for production scalability
- **Containerized Deployment**: Complete Docker setup with NGINX, SSL certificates, and health checks

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   AI Service    │
│   (Dashboard)   │◄──►│   (Django)      │◄──►│   (OpenRouter)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Task Queue    │
                       │   (Celery +     │
                       │    Redis)       │
                       └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   (PostgreSQL)  │
                       └─────────────────┘
```

## Setup Steps

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- PostgreSQL (if running locally)
- Redis (if running locally)

### Environment Configuration

1. **Create Environment File**
   ```bash
   cp .env.example .env
   ```

2. **Configure Environment Variables**
   ```env
   # Database
   DB_NAME=campaign_builder
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_HOST=db
   DB_PORT=5432
   
   # PostgreSQL (for Docker)
   POSTGRES_DB=campaign_builder
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_secure_password
   
   # Django
   SECRET_KEY=your_very_secure_secret_key
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   
   # AI Service
   OPENROUTER_API_KEY=your_openrouter_api_key
   
   # Email Configuration
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_USE_TLS=True
   DEFAULT_FROM_EMAIL=your-email@gmail.com
   
   # Celery & Redis
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

### Production Deployment (Docker)

1. **Clone and Configure**
   ```bash
   git clone <repository-url>
   cd campaign-builder
   # Configure .env file as above
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Run Migrations and Create Superuser**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Access the Application**
   - Dashboard: `http://your-domain/`
   - Admin: `http://your-domain/admin/`
   - API: `http://your-domain/api/campaigns/`

### Local Development Setup

1. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Start Services**
   ```bash
   # Terminal 1: Django development server
   python manage.py runserver
   
   # Terminal 2: Celery worker
   celery -A campaign_builder worker --loglevel=info
   
   # Terminal 3: Redis (if running locally)
   redis-server
   ```

### Testing

```bash
# Run tests
pytest

# Run specific test
pytest campaigns/tests/test_campaigns.py::test_create_daily_campaign
```

## Design Rationale

### 1. **Microservices Architecture**
The system is designed with clear separation of concerns:
- **Django Backend**: Handles API endpoints, data persistence, and business logic
- **Celery Workers**: Manage asynchronous task execution and campaign scheduling
- **Redis**: Provides fast caching and message brokering for distributed tasks
- **PostgreSQL**: Ensures data consistency and supports complex queries with JSON fields

### 2. **AI-Driven Content Generation**
Rather than using static templates, the system employs sophisticated prompt engineering:

```python
def _create_enhanced_prompt(campaign, email_number, total_emails):
    variations = _get_prompt_variations()
    variation = variations[(email_number - 1) % len(variations)]
    
    # Creates context-aware prompts that vary by:
    # - Email sequence position
    # - Day of week
    # - Campaign context
    # - Tone and structure variations
```

This approach ensures each email feels unique while maintaining campaign coherence.

### 3. **Flexible Scheduling System**
The scheduling logic supports both daily and weekly patterns with intelligent next-run calculations:

```python
def _next_run(campaign: Campaign, last_run: datetime.datetime):
    if campaign.schedule_type == Campaign.SCHEDULE_DAILY:
        return last_run + datetime.timedelta(days=1)
    elif campaign.schedule_type == Campaign.SCHEDULE_WEEKLY:
        # Find next day in weekly_days array
        return calculate_next_weekly_run(campaign, last_run)
```

### 4. **Content Personalization**
The system uses multiple prompt variations to create diverse content:
- **Informational/Educational**: Problem-solution structure with value-driven CTAs
- **Promotional**: Benefit-focused content with urgency-based CTAs
- **Personal/Story**: Conversational tone with curiosity-driven CTAs
- **Professional/Direct**: Clear value propositions with specific action CTAs

### 5. **Robust Error Handling**
- Celery retry mechanisms for API failures
- Graceful degradation when AI services are unavailable
- Comprehensive logging for debugging and monitoring
- Email delivery failure handling

## API Reference

### Create Campaign
```http
POST /api/campaigns/
Content-Type: application/json

{
  "name": "Product Launch Series",
  "description": "Weekly emails about our new product features",
  "schedule_type": "weekly",
  "weekly_emails": 2,
  "weekly_days": [1, 3, 5],
  "total_months": 3,
  "ai_agent_id": "openai/gpt-4",
  "recipient_emails": ["user@example.com"]
}
```

### List Campaigns
```http
GET /api/campaigns/
```

### Get Campaign Details
```http
GET /api/campaigns/{campaign_id}/
```

## Extending to Semantic (Vector) Memory

To add semantic memory capabilities for more intelligent content generation, here's how the system could be extended:

### 1. **Vector Database Integration**

Add a vector database like Pinecone, Weaviate, or Qdrant:

```python
# campaigns/vector_memory.py
from pinecone import Pinecone
from openai import OpenAI
import numpy as np

class SemanticMemory:
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = self.pc.Index("campaign-memory")
        self.openai_client = OpenAI()
    
    def store_email_memory(self, campaign_id: str, email_content: str, 
                          metadata: dict):
        """Store email content and metadata in vector database"""
        embedding = self.openai_client.embeddings.create(
            input=email_content,
            model="text-embedding-3-small"
        ).data[0].embedding
        
        self.index.upsert([{
            "id": f"{campaign_id}_{metadata['email_number']}",
            "values": embedding,
            "metadata": {
                "campaign_id": campaign_id,
                "content": email_content,
                **metadata
            }
        }])
    
    def retrieve_similar_content(self, campaign_id: str, query: str, 
                               top_k: int = 5):
        """Find similar past emails for context"""
        query_embedding = self.openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        ).data[0].embedding
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter={"campaign_id": campaign_id},
            include_metadata=True
        )
        
        return results.matches
```

### 2. **Enhanced Campaign Model**

Extend the Campaign model to track semantic patterns:

```python
class Campaign(models.Model):
    # ... existing fields ...
    
    # Semantic memory fields
    content_themes = models.JSONField(default=dict, blank=True)
    performance_patterns = models.JSONField(default=dict, blank=True)
    audience_preferences = models.JSONField(default=dict, blank=True)
    semantic_coherence_score = models.FloatField(default=0.0)
    
    def update_semantic_profile(self, email_content: str, engagement_data: dict):
        """Update campaign's semantic profile based on performance"""
        # Analyze content themes, engagement patterns, etc.
        pass
```

### 3. **Intelligent Content Generation**

Enhance the task to use semantic memory:

```python
@shared_task(bind=True, max_retries=3)
def schedule_campaign_task_with_memory(self, campaign_id: str):
    campaign = Campaign.objects.get(pk=campaign_id)
    memory = SemanticMemory()
    
    # Retrieve relevant past content
    context_emails = memory.retrieve_similar_content(
        campaign_id=str(campaign.id),
        query=campaign.description or campaign.name,
        top_k=3
    )
    
    # Build context-aware prompt
    prompt = _create_semantic_prompt(
        campaign=campaign,
        past_context=context_emails,
        email_number=get_current_email_number(campaign)
    )
    
    # Generate content
    email_content = generate_ai_content(prompt)
    
    # Store in semantic memory
    memory.store_email_memory(
        campaign_id=str(campaign.id),
        email_content=email_content,
        metadata={
            "email_number": get_current_email_number(campaign),
            "timestamp": timezone.now().isoformat(),
            "schedule_type": campaign.schedule_type
        }
    )
    
    # Send email and continue scheduling...
```

### 4. **Semantic-Aware Prompt Engineering**

Create prompts that leverage past performance:

```python
def _create_semantic_prompt(campaign, past_context, email_number):
    base_prompt = _create_enhanced_prompt(campaign, email_number, campaign.total_emails)
    
    if past_context:
        context_section = "PAST CONTENT ANALYSIS:\n"
        for match in past_context:
            context_section += f"- Email #{match.metadata['email_number']}: "
            context_section += f"'{match.metadata['content'][:100]}...'\n"
        
        context_section += "\nGUIDELINES:\n"
        context_section += "- Build upon successful themes from past emails\n"
        context_section += "- Avoid repeating exact phrases or concepts\n"
        context_section += "- Maintain thematic coherence while introducing fresh perspectives\n"
        
        return f"{base_prompt}\n\n{context_section}"
    
    return base_prompt
```

### 5. **Performance Analytics**

Add engagement tracking and semantic analysis:

```python
class EmailEngagement(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    email_number = models.PositiveIntegerField()
    sent_at = models.DateTimeField()
    
    # Engagement metrics
    opens = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    replies = models.PositiveIntegerField(default=0)
    
    # Semantic analysis
    content_embedding = models.JSONField(default=list)  # Store embedding vector
    topic_clusters = models.JSONField(default=list)
    sentiment_score = models.FloatField(default=0.0)
    
    def analyze_performance_patterns(self):
        """Analyze which content patterns perform best"""
        # Use vector similarity to find high-performing content patterns
        pass
```

### Benefits of Semantic Memory Extension

1. **Content Coherence**: Ensures emails build upon each other thematically
2. **Performance Learning**: Identifies which content types resonate with audiences
3. **Personalization**: Adapts content based on engagement patterns
4. **Creativity Balance**: Maintains novelty while leveraging successful patterns
5. **Scalability**: Allows campaigns to improve over time autonomously

This semantic memory system would transform Campaign Builder from a scheduling tool into an intelligent content strategist that learns and adapts based on real-world performance data.