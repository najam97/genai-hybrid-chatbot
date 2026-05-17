# Hybrid Chatbot Usage Examples

This document provides practical examples of how to use the Hybrid Chatbot system.

## Quick Start

### 1. Initialize Database

```bash
python scripts/init_db.py
```

Sample output:
```
Initializing Hybrid Chatbot Database...
--------------------------------------------------
✓ Database schema created successfully
✓ Populated customers table with 10 records
✓ Populated products table with 10 records
✓ Populated orders table with 47 records
--------------------------------------------------
✓ Database successfully initialized at data/mock_db.sqlite
```

### 2. Run the Chatbot

```bash
python main.py
```

## Example Conversations

### Example 1: SQL Query (Structured Data)

```
You: How many orders were placed in the last 30 days?

[Router] Route: SQL | Confidence: 0.98
[Router] Reasoning: User is asking for a metric/count, clear SQL requirement

Bot: Based on the database records, there were 12 orders placed in the last 30 days. 
These orders totaled $2,847.53 in revenue.
```

**Behind the scenes:**
1. Query Classifier routes to SQL (high confidence)
2. SQL Pipeline generates: `SELECT COUNT(*) FROM orders WHERE order_date >= DATE('now', '-30 days')`
3. Query executed safely (read-only validation passed)
4. LLM formats raw data into natural language response

---

### Example 2: Vector Query (Unstructured Data)

```
You: What is your refund policy?

[Router] Route: VECTOR | Confidence: 0.96
[Router] Reasoning: User asking for policy information, not metrics

Bot: [Source: Return Policy]
Our return policy allows refunds within 30 days of purchase. Items must be in 
original condition with all packaging. Refunds are processed within 5-7 business 
days after we receive the returned item.
```

**Behind the scenes:**
1. Query Classifier routes to VECTOR (high confidence)
2. Vector Pipeline retrieves documents with keyword matching
3. LLM generates response grounded in retrieved documents
4. Hallucination prevention: LLM refuses to make up policies

---

### Example 3: Ambiguous Query Resolution

```
You: Tell me about orders policy

[Router] Route: VECTOR | Confidence: 0.85
[Router] Reasoning: "About orders policy" suggests explanation, not metrics

Bot: [Source: Order Policy]
Orders are processed within 24 hours of placement. You will receive an order 
confirmation email with tracking information. Orders cannot be modified after 
they enter the fulfillment stage. Cancellations are accepted up to 12 hours 
after order placement.
```

**Key insight:**
- "orders" could be confused with order metrics
- Router uses semantic understanding (not regex) to determine it's asking for policy
- Confidence is 0.85 (lower than clear cases) but still high enough

---

### Example 4: Multi-Turn Conversation

```
You: Show me top customers by spending

[Router] Route: SQL | Confidence: 0.97
Bot: The top 5 customers by spending are:
1. Sarah Johnson - $4,250.00
2. Michael Brown - $3,890.00
3. Emma Wilson - $3,620.00
4. David Lee - $3,410.00
5. James Taylor - $3,105.00

You: How many orders did the top customer place?

[Router] Route: SQL | Confidence: 0.96 (context-aware)
Bot: Sarah Johnson placed 6 orders in our system.

You: What's our shipping policy for her location?

[Router] Route: VECTOR | Confidence: 0.93
Bot: [Source: Shipping Information]
We offer free shipping on orders over $50. Standard shipping takes 5-7 
business days. Express shipping (2-3 days) is available for an additional fee.
```

**Key features:**
- System maintains conversation context
- Router uses prior messages to inform classification
- Natural back-and-forth dialogue flow
- Correct routing despite implicit references

---

### Example 5: Error Handling and Graceful Degradation

```
You: What are the secret quantum computing features?

[Router] Route: VECTOR | Confidence: 0.72
Bot: I do not have enough information to answer that question. 
Please contact our support team at support@company.com for assistance.
```

**Safety mechanisms:**
- Vector Pipeline explicitly prevents hallucination
- Returns admission of knowledge gap instead of making up features
- Provides support contact for further help

---

## Programmatic Usage

### Using the Chatbot in Python Code

```python
from main import HybridChatbot

# Initialize
bot = HybridChatbot()

# Single query
response = bot.chat("How many customers signed up last month?")
print(f"Response: {response}")

# Multi-turn conversation
bot.chat("Show me top products by revenue")
bot.chat("What's the average price?")
bot.chat("Can you recommend which to promote?")

# Access conversation history
history = bot.get_conversation_history()
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

# Clear and reset
bot.clear_history()
```

---

### Using Individual Pipelines

```python
import openai
from pipelines.sql_pipeline import SQLPipeline
from pipelines.vector_pipeline import VectorPipeline

client = openai.Client()

# SQL Pipeline
sql_pipeline = SQLPipeline(
    db_path="data/mock_db.sqlite",
    client=client,
    model="gpt-4o"
)
result = sql_pipeline.run("Average order value by country?")
print(result)

# Vector Pipeline
vector_pipeline = VectorPipeline(client=client)
result = vector_pipeline.run("Do you have a warranty?")
print(result)
```

---

### Using the Query Classifier

```python
from core.router import QueryClassifier

classifier = QueryClassifier(client=client)

# Single classification
decision = classifier.classify("Total sales last quarter?")
print(f"Route: {decision.route}")
print(f"Confidence: {decision.confidence}")
print(f"Reasoning: {decision.reasoning}")

# Context-aware classification
from core.state import ConversationState

state = ConversationState()
state.add_message("user", "Show me Q1 sales")
state.add_message("assistant", "Q1 sales were $500k")

decision = classifier.classify_with_context(
    "What about Q2?",
    conversation_history=state.get_conversation_history()
)
# Router understands "Q2" in context of prior Q1 question
```

---

## Configuration Examples

### Using Custom Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4-turbo
DB_PATH=/path/to/custom.db
LOG_LEVEL=DEBUG
```

The `Config` class automatically loads these values.

---

### Running with Different Settings

```python
import os
from core.config import Config

# Override before creating bot
os.environ['OPENAI_MODEL'] = 'gpt-3.5-turbo'
os.environ['LOG_LEVEL'] = 'DEBUG'

from main import HybridChatbot
bot = HybridChatbot()  # Uses overridden values
```

---

## Performance Monitoring

### Analyzing Routing Decisions

```python
from main import HybridChatbot

bot = HybridChatbot()

test_queries = [
    "How many orders last month?",
    "What's your return policy?",
    "Top 10 customers by spending",
    "Tell me about shipping",
    "Revenue trend this year"
]

for query in test_queries:
    bot.chat(query)

# Get detailed history with routing metadata
history = bot.state.get_conversation_history(include_metadata=True)
for msg in history:
    if msg['role'] == 'assistant':
        print(f"Route: {msg['metadata']['route']}")
        print(f"Confidence: {msg['metadata']['confidence']:.2f}")
```

---

### Logging and Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Now run bot to see detailed execution logs
from main import HybridChatbot
bot = HybridChatbot()
bot.chat("Your query here")

# Output will show:
# [DEBUG] Classifying query: Your query here
# [DEBUG] Generated SQL: SELECT * FROM ...
# [DEBUG] Step 1: Retrieving relevant documents
# etc.
```

---

## Testing Examples

### Running Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_components.py::TestQueryClassifier -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

---

## Common Questions

### Q: How do I add a new data source?

**A:** Create a new pipeline class:

```python
# pipelines/new_pipeline.py
class NewPipeline:
    def __init__(self, client: openai.Client, **kwargs):
        self.client = client
    
    def run(self, user_query: str) -> str:
        # Your implementation
        return response

# Update core/router.py to add new route type
# Update main.py to initialize new pipeline
```

---

### Q: How do I improve routing accuracy?

**A:** 

1. Adjust the system prompt in `QueryClassifier.SYSTEM_PROMPT`
2. Use `classify_with_context()` for multi-turn awareness
3. Log confidence scores and analyze misroutes
4. Add more examples to the router's system prompt

```python
# Analyze misroutes
low_confidence_decisions = [
    d for d in decisions if d.confidence < 0.75
]
```

---

### Q: How do I prevent SQL injection attempts?

**A:** Multiple layers are already in place:

1. Keyword validation (blocks DROP, DELETE, etc.)
2. Query structure validation (must start with SELECT)
3. Comment removal before validation
4. Read-only database user (in production)
5. Parameterized query execution (in future version)

For production, also use database-level access controls.

---

### Q: How do I integrate a real vector database?

**A:** Replace the mock retrieval in `VectorPipeline`:

```python
# pipelines/vector_pipeline.py
import faiss

class VectorPipeline:
    def __init__(self, vector_db_path: str, client: openai.Client):
        self.index = faiss.read_index(vector_db_path)
        self.client = client
    
    def _retrieve_documents(self, query: str, top_k: int = 3):
        # Embed query
        query_embedding = self.client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        ).data[0].embedding
        
        # Search FAISS index
        distances, indices = self.index.search(
            np.array([query_embedding]), k=top_k
        )
        # Fetch documents and return
```

---

## Performance Benchmarks

**Typical response times (with OpenAI API):**

- **SQL Query**: 2-3 seconds (SQL generation + execution + formatting)
- **Vector Query**: 1-2 seconds (retrieval + generation)
- **Router Decision**: 0.5-1 second
- **Full round trip**: 3-4 seconds

Latency can be improved with:
- Caching frequently answered questions
- Async/parallel execution of pipelines
- Local embeddings instead of API calls

---

## Next Steps

1. **Customize Knowledge Base**: Edit `MOCK_KNOWLEDGE_BASE` in `vector_pipeline.py`
2. **Add Real Data**: Replace mock database with your own
3. **Integrate Vector DB**: Swap mock retrieval with FAISS/Pinecone
4. **Deploy**: Wrap with FastAPI and deploy to cloud
5. **Monitor**: Add metrics collection and observability

See README.md for architecture documentation and deployment guidelines.
