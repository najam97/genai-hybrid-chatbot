# Azure OpenAI Setup Guide

This guide explains how to configure the Hybrid Chatbot to use Azure OpenAI instead of the standard OpenAI API.

## Why Azure OpenAI?

Azure OpenAI provides:
- Integration with Azure security and compliance features
- VPC/VNet isolation
- Managed services with SLA
- Enterprise-grade support
- Integration with Azure AD for authentication

## Prerequisites

1. **Azure Subscription** with access to Azure OpenAI service
2. **Azure OpenAI Resource** created in Azure Portal
3. **Deployment** of a model (gpt-4, gpt-35-turbo, etc.) in your Azure OpenAI resource
4. Python 3.9+ with the latest OpenAI SDK (`pip install openai>=1.3.0`)

## Step-by-Step Setup

### 1. Get Your Azure OpenAI Credentials

In the **Azure Portal**:

1. Navigate to your **Azure OpenAI Resource**
2. Go to **Keys and Endpoint** in the left sidebar
3. Copy the following values:
   - **Endpoint**: URL like `https://your-resource.openai.azure.com/`
   - **Key**: One of the two API keys provided

4. Go to **Deployments** in the left sidebar
5. Note the **Deployment Name** of your model (e.g., `gpt-4o`, `gpt-35-turbo`)

### 2. Update Environment Variables

Edit your `.env` file:

```env
# LLM Provider
LLM_PROVIDER=azure

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_MODEL=gpt-4o
AZURE_API_VERSION=2024-02-15-preview

# Database Configuration
DB_PATH=data/mock_db.sqlite

# Routing Configuration
ROUTING_TEMPERATURE=0.0

# Logging
LOG_LEVEL=INFO
```

**Key points:**
- `LLM_PROVIDER=azure` tells the system to use Azure OpenAI
- `AZURE_OPENAI_ENDPOINT` must end with `/` (e.g., `https://myresource.openai.azure.com/`)
- `AZURE_OPENAI_DEPLOYMENT` should match your deployment name in Azure Portal
- `AZURE_API_VERSION` should be a current supported version (see [Azure OpenAI API Versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference))

### 3. Verify Setup

```bash
# Run database initialization
python scripts/init_db.py

# Test the chatbot
python main.py
```

If configured correctly, you'll see:
```
============================================================
HYBRID CHATBOT - Production Architecture Demo
...
2026-05-17 12:15:00,000 - __main__ - INFO - Initializing Azure OpenAI client
2026-05-17 12:15:00,100 - __main__ - INFO - Azure OpenAI client initialized (deployment: gpt-4o)
...
Hybrid Chatbot successfully initialized
============================================================

You: How many customers do we have?
[Router] Route: SQL | Confidence: 0.98
Bot: Based on the database, there are 10 registered customers...
```

---

## Troubleshooting

### Error: "AZURE_OPENAI_ENDPOINT is not set"

**Solution:** Ensure your `.env` file has:
```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

Note the trailing `/` in the endpoint URL.

### Error: "Invalid API key"

**Solution:** 
- Verify the API key matches exactly (copy from Azure Portal, no extra spaces)
- Check the API key hasn't expired
- Try the other key from Azure Portal

### Error: "Deployment not found"

**Solution:**
- Check the deployment name matches exactly in Azure Portal
- Go to **Deployments** in your Azure OpenAI resource
- Copy the exact deployment name
- Deployment names are case-sensitive

### Error: "Invalid API version"

**Solution:**
- Check the API version is supported for your region
- Use `2024-02-15-preview` or check [Azure docs for current versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)
- Ensure you have the latest OpenAI SDK: `pip install --upgrade openai`

### Slow Response Times

**Solution:**
- Check your Azure region (lower latency for regions closer to you)
- Verify network connectivity to Azure
- Check if you're hitting rate limits (contact Azure support)
- Consider enabling caching for repeated queries

---

## Switching Back to OpenAI

To use standard OpenAI API instead:

1. Update `.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

2. Restart the chatbot:
```bash
python main.py
```

---

## Environment Variables Reference

| Variable | Required | Default | Example |
|----------|----------|---------|---------|
| `LLM_PROVIDER` | Yes | `openai` | `azure` |
| `AZURE_OPENAI_API_KEY` | Yes* | - | (24+ char key) |
| `AZURE_OPENAI_ENDPOINT` | Yes* | - | `https://myorg.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | Yes* | - | `gpt-4o` |
| `AZURE_OPENAI_MODEL` | No | `gpt-4o` | `gpt-4o` |
| `AZURE_API_VERSION` | No | `2024-02-15-preview` | `2024-02-15-preview` |
| `OPENAI_API_KEY` | Yes** | - | `sk-...` |
| `OPENAI_MODEL` | No | `gpt-4o` | `gpt-4o` |

*Required only if `LLM_PROVIDER=azure`
**Required only if `LLM_PROVIDER=openai`

---

## Production Deployment Notes

### Security Best Practices

1. **Never commit `.env` to version control**
   - Use `.gitignore` to exclude `.env`
   - Use Azure Key Vault or similar for production

2. **Rotate API Keys Regularly**
   - Azure Portal allows key rotation without downtime
   - Keep two keys: one active, one for rotation

3. **Use Managed Identity (Recommended)**
   - If running on Azure VMs/App Service, use Managed Identity instead of API keys
   - Update code to use:
   ```python
   from azure.identity import DefaultAzureCredential
   
   credential = DefaultAzureCredential()
   # Instead of passing API key
   ```

4. **Network Security**
   - Enable Private Endpoints for your Azure OpenAI resource
   - Restrict access to specific VNets/subnets
   - Use Network Security Groups (NSGs) appropriately

### Monitoring and Logging

Azure provides built-in monitoring:

1. **Azure Monitor Metrics**
   - Token usage
   - API call counts
   - Error rates
   - Response times

2. **Application Insights**
   - Detailed request logging
   - Performance tracking
   - Dependency analysis

Enable via Azure Portal → Your OpenAI Resource → Settings → Diagnostic settings.

### Cost Optimization

- **Monitor token usage** to avoid unexpected charges
- **Set up alerts** when usage exceeds thresholds
- **Use caching** for frequently asked questions
- **Batch requests** when possible

---

## Additional Resources

- [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure OpenAI Python SDK](https://github.com/openai/openai-python)
- [API Reference](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)
- [Azure Security Best Practices](https://learn.microsoft.com/en-us/azure/security/)

---

## Support

If you encounter issues:

1. Check the **troubleshooting** section above
2. Review Azure OpenAI [documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
3. Contact Azure Support through Azure Portal
4. Check OpenAI SDK [GitHub Issues](https://github.com/openai/openai-python/issues)

---

**Last Updated:** May 17, 2026
