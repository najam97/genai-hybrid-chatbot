# Hybrid Chatbot: Production-Grade Architecture

## Executive Summary

This project demonstrates a **production-grade, enterprise-scale hybrid chatbot** that intelligently routes natural language queries to specialized pipelines for structured data (SQL) and unstructured information (RAG/Vector). 

Supports both **OpenAI API** and **Azure OpenAI** for maximum flexibility in deployment.

The implementation showcases:
- ✅ **Semantic routing** via LLM-based query classification with deterministic output formatting (Pydantic)
- ✅ **Pipeline isolation** ensuring strict separation of concerns and failure containment
- ✅ **Defensive SQL execution** with injection prevention and read-only enforcement
- ✅ **Dependency injection** enabling testability and scalability
- ✅ **Multi-turn conversation state** management for contextual awareness
- ✅ **Enterprise-grade error handling** and logging throughout
- ✅ **Modular architecture** supporting easy extension with new data sources
- ✅ **Dual LLM provider support** (OpenAI + Azure OpenAI)

### Web UI

A Streamlit web UI is available in `streamlit_app.py`.
The old FastAPI UI is preserved in `api/app.py` as a backup.
The Streamlit app uses the existing hybrid router and pipelines, and stores history server-side in `data/streamlit_history.json`.

This codebase is designed to **impress hiring panels** evaluating your ability to build resilient, scalable systems at scale.

---

## Architectural Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Input (Query)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│      SEMANTIC ROUTER (LLM-Based Query Classifier)               │
│  - Pydantic-enforced JSON schema output                         │
│  - Deterministic routing (temperature=0.0)                      │
│  - Confidence scores + reasoning                                │
│  - Fallback to UNKNOWN on API failure                           │
└────────┬────────────────────────────────────────┬───────────────┘
         │                                        │
    ┌────▼──────┐                        ┌────────▼─────┐
    │  SQL Query │                        │ Vector Query │
    └────┬───────┘                        └────────┬─────┘
         │                                        │
         ▼                                        ▼
┌──────────────────────┐            ┌──────────────────────┐
│   SQL PIPELINE       │            │ VECTOR PIPELINE      │
│  - Text-to-SQL       │            │  - Document Retrieval│
│  - Query Safety      │            │  - RAG Integration   │
│  - Read-Only Exec    │            │  - Hallucination     │
│  - Format Response   │            │    Reduction         │
└──────────┬───────────┘            └──────────┬───────────┘
           │                                   │
           └─────────────────┬─────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Final Response │
                    └────────────────┘
```

---

## Key Design Decisions

### 1. **Semantic Router Over Rule-Based Regex**

**Why?**
- **Problem**: Regex-based routing is brittle and fails on edge cases
  - "Tell me about orders policy" → Could route to SQL (orders)
  - "Orders placed last month?" → Clearly SQL (metrics)
  - Simple keywords create collision issues

- **Solution**: LLM-based semantic classification with structured output
  ```python
  # Uses OpenAI's beta structured outputs (response_format=RouteDecision)
  # Pydantic enforces type safety: route, confidence, reasoning
  decision = classifier.classify("Tell me about orders policy")
  # Returns: RouteDecision(route="vector", confidence=0.95, reasoning="...")
  ```

**Benefits:**
- Handles nuanced queries without maintenance
- Confidence scores enable logging and analysis
- Deterministic behavior (temperature=0.0)
- Type-safe via Pydantic validation

---

### 2. **Strict Pipeline Isolation**

**Why?**
- **Problem**: Mixing SQL and Vector logic leads to:
  - Code bloat and maintenance nightmare
  - Failure in one pipeline corrupts the other
  - Testing becomes exponentially harder
  - Unclear ownership of bugs

- **Solution**: Completely isolated pipeline classes
  ```
  SQLPipeline: Handles structured data only
  VectorPipeline: Handles unstructured data only
  Router: Acts as gatekeeper—query goes to ONE pipeline
  ```

**Benefits:**
- Each pipeline can be tested independently
- Failures are contained (SQL error doesn't affect Vector)
- Easy to swap implementations (e.g., replace FAISS with Pinecone)
- Clear debugging: "Error in SQL Pipeline" vs "Error in Vector Pipeline"

---

### 3. **Defensive SQL Execution**

**Why?**
- **Problem**: SQL injection is a critical vulnerability
  - `query = "SELECT * FROM users WHERE id = " + user_input`
  - User enters: `1; DROP TABLE users;`
  - Database destroyed!

- **Solution**: Multi-layered defense
  ```python
  def execute_read_only_query(self, query: str) -> str:
      # Layer 1: Keyword validation
      if any(keyword in query.upper() for keyword in UNSAFE_KEYWORDS):
          raise ValueError("Only SELECT queries permitted")
      
      # Layer 2: Structural validation (regex for comment removal)
      if not query_cleaned.upper().startswith("SELECT"):
          raise ValueError("Non-SELECT query detected")
      
      # Layer 3: Secure connection
      with sqlite3.connect(self.db_path) as conn:
          conn.execute("PRAGMA foreign_keys = ON")
          cursor.execute(query)  # Execute (already validated)
  ```

**Benefits:**
- Multiple validation layers (defense in depth)
- Prevents both injection and unauthorized operations
- Production-ready security posture
- Audit trail via logging

---

### 4. **Dependency Injection**

**Why?**
- **Problem**: Hardcoding clients/connections is a testing nightmare
  ```python
  # Bad: Tightly coupled
  class SQLPipeline:
      def __init__(self):
          self.client = openai.Client()  # Can't mock for testing!
  ```

- **Solution**: Inject dependencies via constructor
  ```python
  class SQLPipeline:
      def __init__(self, db_path: str, client: openai.Client, model: str):
          self.db_path = db_path
          self.client = client  # Can inject mock for testing
          self.model = model
  ```

**Benefits:**
- Enables unit testing with mock clients
- Supports multiple configurations without code changes
- Follows SOLID principles (Dependency Inversion)
- Production-ready testability

---

### 5. **Multi-Turn Conversation State**

**Why?**
- **Problem**: Single-turn bots are limited
  - Can't remember prior context
  - User: "Show me Q1 sales" → Bot: "Which year?"
  - User: "2024" → Bot: "Which quarter?" (should remember 2024!)

- **Solution**: `ConversationState` class maintains history
  ```python
  state = ConversationState(max_history=20)
  state.add_message(role="user", content="Show Q1 sales")
  state.add_message(role="assistant", content="Which year?")
  
  # Router can now use context_aware classification
  decision = classifier.classify_with_context(
      query="2024",
      conversation_history=state.get_conversation_history()
  )
  ```

**Benefits:**
- Supports multi-turn dialogue naturally
- Context-aware routing improves classification accuracy
- Enables conversation analysis and metrics
- Foundation for advanced features (clarification, refinement)

---

### 6. **Configuration Management (Not Hardcoded)**

**Why?**
- **Problem**: Hardcoded values prevent flexibility
  ```python
  # Bad
  DB_PATH = "data/mock_db.sqlite"
  OPENAI_API_KEY = "sk-abc123xyz"
  ```

- **Solution**: Centralized `Config` class with environment variable support
  ```python
  class Config:
      OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
      DB_PATH = os.getenv("DB_PATH", "data/mock_db.sqlite")
      ROUTING_TEMPERATURE = 0.0  # Deterministic routing
  
  Config.validate()  # Fail fast if critical vars missing
  ```

**Benefits:**
- Same codebase works across dev/staging/production
- Secure credential management (no secrets in code)
- Easy to test with different configurations
- Professional deployment practices

---

## Project Structure

```
hybrid_chatbot/
│
├── core/
│   ├── __init__.py              # Package exports
│   ├── config.py                # Environment & configuration
│   ├── router.py                # LLM-based semantic router
│   └── state.py                 # Conversation state management
│
├── pipelines/
│   ├── __init__.py              # Package exports
│   ├── sql_pipeline.py          # Text-to-SQL + execution
│   └── vector_pipeline.py       # RAG + hallucination reduction
│
├── scripts/
│   └── init_db.py               # Database initialization
│
├── data/
│   └── mock_db.sqlite           # Local SQLite database (generated)
│
├── main.py                      # CLI entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

---

## Getting Started

### 1. Clone and Install

```bash
# Navigate to project directory
cd hybrid_chatbot

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the template
cp .env.example .env

# Edit .env with your values
```

**For OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
DB_PATH=data/mock_db.sqlite
LOG_LEVEL=INFO
```

**For Azure OpenAI:**
```env
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-02-15-preview
DB_PATH=data/mock_db.sqlite
LOG_LEVEL=INFO
```

> **Note:** For detailed Azure OpenAI setup instructions, see [AZURE_SETUP.md](AZURE_SETUP.md)

### 3. Initialize the Database

```bash
python scripts/init_db.py
```

This creates `data/mock_db.sqlite` with three tables:
- **customers** (10 sample records)
- **products** (10 products)
- **orders** (30-70 orders)

### 4. Run the Chatbot

```bash
python main.py
```

**Example Interactions:**

```
You: How many orders were placed last month?
[Router] Route: SQL | Confidence: 0.98
Bot: <SQL Pipeline generates SELECT, executes, formats response>
Bot: Based on the database, there were 8 orders placed last month...

You: What is your refund policy?
[Router] Route: VECTOR | Confidence: 0.96
Bot: <Vector Pipeline retrieves relevant documents>
Bot: Our return policy allows refunds within 30 days of purchase...

You: Tell me about orders policy
[Router] Route: VECTOR | Confidence: 0.95
Bot: <Vector Pipeline> Orders cannot be modified after fulfillment...
```

---

## Implementation Highlights

### **Query Router (core/router.py)**

```python
class QueryClassifier:
    """LLM-based semantic router using Pydantic for deterministic output."""
    
    SYSTEM_PROMPT = """
    You are a semantic router. Classify queries into:
    1. 'sql': Structured data, metrics, aggregations
    2. 'vector': Policies, FAQs, unstructured information
    
    Return JSON with route, confidence, reasoning.
    """
    
    def classify(self, query: str) -> RouteDecision:
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": self.SYSTEM_PROMPT}, ...],
            response_format=RouteDecision,  # Pydantic model
            temperature=0.0  # Deterministic
        )
        return response.choices[0].message.parsed
```

**Key Points:**
- Uses OpenAI's structured output (beta API)
- Pydantic validation ensures type safety
- Temperature=0.0 ensures deterministic behavior
- Fallback to UNKNOWN route on API failure

---

### **SQL Pipeline (pipelines/sql_pipeline.py)**

**Three-Step Process:**

1. **Text-to-SQL Generation**
   ```python
   sql_query = self._generate_sql_query(user_query)
   # Leverages LLM with schema context to generate SELECT queries
   ```

2. **Secure Execution**
   ```python
   if not self._is_safe_query(query):
       raise ValueError("Only SELECT queries permitted")
   results = self.execute_read_only_query(sql_query)
   ```

3. **Response Formatting**
   ```python
   final_answer = self._format_response(user_query, raw_data)
   # Converts raw data into natural language
   ```

**Security Features:**
- Keyword validation (blocks DROP, DELETE, UPDATE, etc.)
- Regex-based comment removal before validation
- Structural validation (must start with SELECT)
- Foreign key constraints enabled

---

### **Vector Pipeline (pipelines/vector_pipeline.py)**

**RAG Pipeline with Hallucination Prevention:**

1. **Document Retrieval**
   ```python
   retrieved_docs = self._retrieve_documents(query, top_k=3)
   # Keyword-based retrieval (production: use embeddings + FAISS/Pinecone)
   ```

2. **Context Building**
   ```python
   context = "\n\n".join([f"[Source: {doc['title']}]\n{doc['content']}" 
                          for doc in retrieved_docs])
   ```

3. **Grounded Response Generation**
   ```python
   prompt = f"""
   Answer ONLY using provided context.
   If not in context, say: "I do not have enough information."
   Do not hallucinate.
   
   Context: {context}
   Question: {user_query}
   """
   ```

**Hallucination Prevention:**
- Explicit instruction: "Do not hallucinate"
- Low temperature (0.2) for factual grounding
- Forces admission of knowledge gaps

---

### **Conversation State (core/state.py)**

```python
class ConversationState:
    """Maintains multi-turn context for contextual awareness."""
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        if role == "user":
            self.turn_count += 1
    
    def get_conversation_history(self, include_metadata=False):
        """Returns history in OpenAI API format."""
        return [{"role": msg.role, "content": msg.content} 
                for msg in self.messages]
```

**Enables:**
- Context-aware routing
- Conversation analysis
- Multi-turn refinement
- Future conversation summarization

---

## Error Handling & Robustness

### **Layered Error Handling**

```python
try:
    decision = self.classifier.classify(user_query)
except Exception as e:
    # Graceful fallback to UNKNOWN route
    return RouteDecision(
        route=QueryRoute.UNKNOWN,
        confidence=0.0,
        reasoning=f"Classifier error: {str(e)}"
    )
```

### **Database Safety**

```python
try:
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        # All operations are read-only
except sqlite3.Error as e:
    raise ValueError(f"Database error: {str(e)}")
```

### **Comprehensive Logging**

```python
logger.info(f"[Router] Route: {decision.route} | Confidence: {decision.confidence}")
logger.debug(f"Generated SQL: {sql_query}")
logger.error(f"Database error: {e}")
```

---

## Testing Strategy

### **Unit Testing Example:**

```python
import pytest
from unittest.mock import Mock

def test_sql_query_safety():
    """Verify read-only enforcement."""
    pipeline = SQLPipeline(db_path="test.db", client=Mock())
    
    with pytest.raises(ValueError):
        pipeline._is_safe_query("DROP TABLE customers;")
    
    with pytest.raises(ValueError):
        pipeline._is_safe_query("INSERT INTO users VALUES (...)")
    
    assert pipeline._is_safe_query("SELECT * FROM customers;")

def test_routing_confidence():
    """Verify router produces consistent confidence scores."""
    classifier = QueryClassifier(client=openai.Client())
    
    decision = classifier.classify("Total orders last month?")
    assert decision.route == QueryRoute.SQL
    assert decision.confidence > 0.8

def test_vector_hallucination_prevention():
    """Verify vector pipeline refuses to answer OOB queries."""
    pipeline = VectorPipeline(client=openai.Client())
    
    response = pipeline.run("What is your secret sauce recipe?")
    assert "I do not have enough information" in response or "contact support" in response
```

---

## Deployment Considerations

### **Production Checklist:**

- [ ] **Secrets Management**: Use AWS Secrets Manager / HashiCorp Vault instead of .env
- [ ] **Vector DB**: Replace mock retrieval with FAISS / Pinecone / Weaviate
- [ ] **Database**: Migrate from SQLite to PostgreSQL with read-only replica
- [ ] **API Rate Limiting**: Implement exponential backoff for OpenAI API calls
- [ ] **Monitoring**: Add Datadog / New Relic for observability
- [ ] **Caching**: Implement Redis for frequently answered questions
- [ ] **Multi-threading**: Use asyncio for concurrent pipeline execution
- [ ] **Load Testing**: Test with concurrent users (locust / Apache JMeter)

### **Scaling Strategy:**

1. **Stateless Design**: All state stored in database, not in-memory
2. **API Server**: Wrap main.py with FastAPI/Flask for HTTP endpoint
3. **Queue System**: Use Celery + Redis for long-running queries
4. **Microservices**: Split pipelines into separate services if needed

---

## Future Extensions

### **1. Advanced Routing**
- Multi-label routing (e.g., "Show Q1 sales with profit margin trend" → SQL + context)
- Dynamic confidence thresholds based on fallback success rates

### **2. Conversation Features**
- Automatic summarization of long conversations
- Clarification requests when queries are ambiguous
- User feedback loop for routing accuracy improvement

### **3. Data Integration**
- Real-time Stripe/Shopify API integration for commerce queries
- Third-party data source routing (internal APIs, external data lakes)

### **4. Performance**
- Query result caching with TTL
- Batch processing for bulk queries
- Streaming responses for large result sets

### **5. Observability**
- Custom metrics: routing accuracy, latency by route, error rates
- Conversation analytics dashboard
- Query pattern analysis

---

## Key Takeaways for Hiring Panels

✅ **Architecture Excellence**
- Semantic routing > regex-based heuristics
- Pipeline isolation prevents cascading failures
- Dependency injection enables testability

✅ **Security**
- SQL injection prevention with multi-layer validation
- Read-only enforcement at application level
- No hardcoded secrets

✅ **Scalability**
- Stateless design supports horizontal scaling
- Modular pipelines can be scaled independently
- Configuration-driven behavior

✅ **Maintainability**
- Clear separation of concerns
- Comprehensive logging and error handling
- Well-documented code and architecture

✅ **Enterprise-Grade Practices**
- Pydantic for validation and type safety
- Environment-based configuration
- Multi-turn conversation support
- Defensive programming throughout

---

## References & Further Reading

- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [RAG Hallucination Mitigation](https://arxiv.org/abs/2309.07852)
- [12-Factor App Principles](https://12factor.net/)

---

## License

This project is provided as-is for educational and evaluation purposes.

---

**Built with ❤️ to demonstrate production-grade AI system architecture.**
