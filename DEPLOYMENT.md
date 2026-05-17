# Deployment Guide: Hybrid Chatbot

This guide provides step-by-step instructions for deploying the Hybrid Chatbot to production environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Containerization](#docker-containerization)
3. [Cloud Deployment (AWS/GCP/Azure)](#cloud-deployment)
4. [Security Hardening](#security-hardening)
5. [Monitoring & Observability](#monitoring--observability)
6. [Scaling Strategy](#scaling-strategy)

---

## Local Development

### Prerequisites

- Python 3.9+
- Virtual environment (venv/conda)
- OpenAI API key

### Setup Steps

```bash
# Clone repository
git clone <repo-url>
cd hybrid_chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Create .env file
cp .env.example .env
# Edit .env with your OpenAI API key

# Run tests
pytest tests/ -v

# Start development server
python main.py
```

---

## Docker Containerization

### Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data

# Initialize database if not exists
RUN python scripts/init_db.py --no-prompt

# Expose port for API server
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

Create `docker-compose.yml` for local multi-container setup:

```yaml
version: '3.9'

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DB_PATH=/app/data/mock_db.sqlite
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  postgres:  # Optional: Production database
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: chatbot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:  # Optional: Caching layer
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Build and Run

```bash
# Build image
docker build -t hybrid-chatbot:latest .

# Run container
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY \
           -p 8000:8000 \
           -v $(pwd)/data:/app/data \
           hybrid-chatbot:latest

# Using Docker Compose
docker-compose up -d
```

---

## Cloud Deployment

### AWS ECS + Fargate

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name hybrid-chatbot

# 2. Build and push image
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag hybrid-chatbot:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/hybrid-chatbot:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/hybrid-chatbot:latest

# 3. Create ECS task definition (task-definition.json)
{
  "family": "hybrid-chatbot",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "chatbot",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/hybrid-chatbot:latest",
      "essential": true,
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ]
    }
  ]
}

# 4. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 5. Create Fargate service
aws ecs create-service \
  --cluster default \
  --service-name hybrid-chatbot \
  --task-definition hybrid-chatbot \
  --desired-count 2 \
  --launch-type FARGATE
```

### GCP Cloud Run

```bash
# 1. Create GCP project and enable Cloud Run API
gcloud projects create hybrid-chatbot-project
gcloud config set project hybrid-chatbot-project
gcloud services enable run.googleapis.com

# 2. Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/hybrid-chatbot-project/chatbot:latest

# 3. Deploy to Cloud Run
gcloud run deploy hybrid-chatbot \
  --image gcr.io/hybrid-chatbot-project/chatbot:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60s \
  --max-instances 100
```

### Azure Container Instances

```bash
# 1. Create resource group
az group create --name hybrid-chatbot-rg --location eastus

# 2. Create container registry
az acr create --resource-group hybrid-chatbot-rg \
  --name hybridchatbotacr --sku Basic

# 3. Build and push image
az acr build --registry hybridchatbotacr --image hybrid-chatbot:latest .

# 4. Deploy container instance
az container create \
  --resource-group hybrid-chatbot-rg \
  --name hybrid-chatbot \
  --image hybridchatbotacr.azurecr.io/hybrid-chatbot:latest \
  --cpu 1 --memory 1.5 \
  --port 8000 \
  --environment-variables OPENAI_API_KEY=$OPENAI_API_KEY
```

---

## Security Hardening

### 1. Secrets Management

**Never store secrets in code or .env files in production!**

**AWS Secrets Manager:**
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

OPENAI_API_KEY = get_secret('openai/api-key')
```

**Azure Key Vault:**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret(secret_name):
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url="https://<vault-name>.vault.azure.us", credential=credential)
    return client.get_secret(secret_name).value
```

### 2. Database Security

**Production PostgreSQL with read-only replica:**

```python
# config.py
DATABASE_READ_URL = os.getenv("DATABASE_READ_URL")  # Read-only replica
DATABASE_WRITE_URL = os.getenv("DATABASE_WRITE_URL")  # Write instance

# Use read-only connection for SQL pipeline
conn = psycopg2.connect(DATABASE_READ_URL)
```

**Row-Level Security:**
```sql
-- Only allow SELECT, never allow modifications
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_user;
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM chatbot_user;
```

### 3. API Authentication

Wrap with API gateway and authentication:

```python
# api/main.py (using FastAPI)
from fastapi import FastAPI, Security, HTTPException
from fastapi.security import APIKeyHeader

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/chat")
async def chat(query: str, api_key: str = Security(verify_api_key)):
    bot = HybridChatbot()
    return bot.chat(query)
```

### 4. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, query: str):
    # Process request
    pass
```

### 5. Input Sanitization

```python
import html

def sanitize_input(query: str) -> str:
    # Remove null bytes
    query = query.replace('\0', '')
    # Escape HTML
    query = html.escape(query)
    # Limit length
    return query[:1000]

# In router.py
def classify(self, query: str) -> RouteDecision:
    query = sanitize_input(query)
    # Proceed with classification
```

---

## Monitoring & Observability

### 1. Logging with Structured Output

```python
import json
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Structured logging
logger.info("query_processed", extra={
    "query": query,
    "route": decision.route,
    "confidence": decision.confidence,
    "response_time": elapsed_time
})
```

### 2. Metrics Collection (Prometheus)

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
routing_counter = Counter(
    'queries_routed_total',
    'Total queries routed',
    ['route', 'confidence_level']
)

response_time_histogram = Histogram(
    'response_time_seconds',
    'Response time in seconds',
    ['route']
)

sql_error_counter = Counter(
    'sql_errors_total',
    'Total SQL errors',
    ['error_type']
)

# Record metrics
with response_time_histogram.labels(route='sql').time():
    sql_pipeline.run(query)

routing_counter.labels(
    route=decision.route,
    confidence_level='high' if decision.confidence > 0.9 else 'low'
).inc()
```

### 3. Distributed Tracing (Jaeger)

```python
from jaeger_client import Config

config = Config(
    config={
        'sampler': {
            'type': 'const',
            'param': 1,
        },
        'logging': True,
    },
    service_name='hybrid-chatbot',
)
jaeger_tracer = config.initialize_tracer()

def chat_with_tracing(query):
    with jaeger_tracer.start_active_span('chat') as scope:
        with jaeger_tracer.start_active_span('classify') as span:
            decision = classifier.classify(query)
            span.span.set_tag('route', decision.route.value)
        
        with jaeger_tracer.start_active_span('execute_pipeline') as span:
            response = bot.chat(query)
            span.span.set_tag('status', 'success')
        
        return response
```

### 4. Error Tracking (Sentry)

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production")
)

try:
    response = bot.chat(query)
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise
```

---

## Scaling Strategy

### 1. Horizontal Scaling

**Problem:** Single instance can't handle peak load

**Solution:** Run multiple instances behind load balancer

```bash
# Kubernetes deployment (k8s deployment.yaml)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-chatbot
spec:
  replicas: 3  # Start with 3 instances
  selector:
    matchLabels:
      app: hybrid-chatbot
  template:
    metadata:
      labels:
        app: hybrid-chatbot
    spec:
      containers:
      - name: chatbot
        image: hybrid-chatbot:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: hybrid-chatbot-service
spec:
  selector:
    app: hybrid-chatbot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 2. Caching with Redis

```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)
CACHE_TTL = 3600  # 1 hour

def cache_response(ttl=CACHE_TTL):
    def decorator(func):
        @wraps(func)
        def wrapper(query):
            # Create cache key
            cache_key = f"query:{hash(query)}"
            
            # Try cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = func(query)
            
            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

@cache_response()
def chat_cached(query):
    return bot.chat(query)
```

### 3. Async Processing for Long Queries

```python
from celery import Celery

celery = Celery('chatbot', broker='redis://localhost:6379')

@celery.task
def process_query(query_id, query):
    """Long-running query processing in background."""
    result = bot.chat(query)
    # Store result in database
    db.save_result(query_id, result)

# API endpoint
@app.post("/chat/async")
async def chat_async(query: str):
    query_id = uuid.uuid4()
    # Enqueue task
    process_query.delay(str(query_id), query)
    return {"query_id": str(query_id), "status": "processing"}

@app.get("/chat/result/{query_id}")
async def get_result(query_id: str):
    result = db.get_result(query_id)
    return result if result else {"status": "processing"}
```

### 4. Database Optimization

```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Keep 20 connections open
    max_overflow=40,  # Allow 40 additional connections
    pool_pre_ping=True,  # Test connections before use
)
```

---

## Performance Optimization Checklist

- [ ] Enable response caching for common queries
- [ ] Use async/await for I/O operations
- [ ] Implement database connection pooling
- [ ] Add query result pagination
- [ ] Use CDN for static assets
- [ ] Implement request batching
- [ ] Add rate limiting per user/API key
- [ ] Monitor and optimize hot paths
- [ ] Use lazy loading for large datasets
- [ ] Implement circuit breaker for external APIs

---

## Post-Deployment Validation

```bash
# Health check
curl http://localhost:8000/health

# Load testing
ab -n 1000 -c 10 http://localhost:8000/chat?query="test"

# Monitor logs
docker logs -f hybrid-chatbot

# Check metrics
curl http://localhost:8000/metrics

# Run integration tests
pytest tests/integration/ -v
```

---

## Rollback Strategy

```bash
# Keep previous version running
docker tag hybrid-chatbot:v1 hybrid-chatbot:stable
docker tag hybrid-chatbot:v2 hybrid-chatbot:latest

# If v2 fails, revert
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY hybrid-chatbot:stable

# Kubernetes rollback
kubectl rollout history deployment/hybrid-chatbot
kubectl rollout undo deployment/hybrid-chatbot --to-revision=1
```

---

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and error rates
- **Weekly**: Review performance metrics and slow queries
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and optimize database indexes
- **Yearly**: Disaster recovery drills and load testing

### Version Management

```bash
# Semantic versioning
v1.0.0 = MAJOR.MINOR.PATCH

# Tag releases
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Automated deployments via CI/CD
# (GitHub Actions, GitLab CI, Jenkins, etc.)
```

---

**For additional support or questions, contact the platform engineering team.**
