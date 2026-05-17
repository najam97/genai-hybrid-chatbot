# Quick Start Guide - Hybrid Chatbot

## Option A: Using Azure OpenAI (Recommended for Enterprise)

### 1. Update .env File

Edit `.env` and set:

```env
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_KEY_HERE>.
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-02-15-preview
DB_PATH=data/mock_db.sqlite
LOG_LEVEL=INFO
```

**Important:** Replace `your-resource-name` with your actual Azure resource name.

### 2. Initialize Database

```bash
python scripts/init_db.py
```

### 3. Run Chatbot

```bash
python main.py
```

**Expected Output:**
```
============================================================
HYBRID CHATBOT - Production Architecture Demo
============================================================

[INFO] Initializing Azure OpenAI client
[INFO] Azure OpenAI client initialized (deployment: gpt-4o)
[INFO] Configuration validated successfully
[INFO] Hybrid Chatbot successfully initialized
============================================================

You: How many orders were placed last month?

[Router] Route: SQL | Confidence: 0.98
Bot: Based on the database, there were 12 orders placed in the last 30 days...
```

---

## Option B: Using OpenAI API

### 1. Update .env File

Edit `.env` and set:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
DB_PATH=data/mock_db.sqlite
LOG_LEVEL=INFO
```

### 2. Initialize Database

```bash
python scripts/init_db.py
```

### 3. Run Chatbot

```bash
python main.py
```

### 4. Run Streamlit Frontend

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open the URL shown by Streamlit (usually `http://localhost:8501`).

> The old FastAPI app is preserved in `api/app.py` as a backup.

---

## Troubleshooting

### Error: "AZURE_OPENAI_ENDPOINT is not set"
**Fix:** Your endpoint URL must have a trailing `/`
```env
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/  ← Note the /
```

### Error: "Invalid API key"
**Fix:** 
- Copy the key directly from Azure Portal (Keys and Endpoint section)
- Make sure there are no extra spaces
- Check it hasn't expired

### Error: "Deployment not found"
**Fix:**
- Go to Azure Portal → Your Resource → Deployments
- Use the exact deployment name (case-sensitive)
- Example: `gpt-4o` or `gpt-35-turbo`

### Error: "Database not found"
**Fix:**
```bash
python scripts/init_db.py
```

---

## Configuration Reference

### Azure OpenAI (LLM_PROVIDER=azure)

| Variable | Value | Where to Find |
|----------|-------|---------------|
| `AZURE_OPENAI_API_KEY` | Your API key | Azure Portal → Keys and Endpoint → Key 1 or Key 2 |
| `AZURE_OPENAI_ENDPOINT` | Resource URL | Azure Portal → Keys and Endpoint → Endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name | Azure Portal → Deployments → Name |
| `AZURE_API_VERSION` | `2024-02-15-preview` | [Check here](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference) |

### OpenAI (LLM_PROVIDER=openai)

| Variable | Value | Where to Find |
|----------|-------|---------------|
| `OPENAI_API_KEY` | Your API key | [OpenAI Dashboard](https://platform.openai.com/api-keys) |
| `OPENAI_MODEL` | `gpt-4o` or similar | [Model list](https://platform.openai.com/docs/models) |

---

## Test Your Setup

```bash
# Start the chatbot
python main.py

# Try these test queries:
# 1. SQL Query (Structured Data):
#    "How many customers do we have?"
#    "What's the average order value?"
#    "Show me top 5 products by revenue"

# 2. Vector Query (Policies/FAQs):
#    "What's your refund policy?"
#    "Do you offer free shipping?"
#    "Tell me about warranty"

# 3. Commands:
#    Type 'history' to see conversation
#    Type 'clear' to reset state
#    Type 'exit' to quit
```

---

## Next Steps

- Review [AZURE_SETUP.md](AZURE_SETUP.md) for detailed Azure configuration
- Check [README.md](README.md) for full architecture documentation
- See [EXAMPLES.md](EXAMPLES.md) for usage patterns and examples
- Review [tests/](tests/) for unit testing examples
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

---

## Quick Links

- **OpenAI:** https://platform.openai.com/api-keys
- **Azure Portal:** https://portal.azure.com
- **Azure OpenAI Docs:** https://learn.microsoft.com/en-us/azure/ai-services/openai/
- **OpenAI SDK Docs:** https://github.com/openai/openai-python
