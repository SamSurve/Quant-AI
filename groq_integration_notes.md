# Groq Finance Agent Integration Notes

The backend uses `agno.models.groq.Groq` with `GROQ_API_KEY` supplied only through the backend process environment. The supported model identifier selected for this service is `openai/gpt-oss-120b`; the official Groq model page documents this identifier and its tool-use capability.

The agent retains provider-backed YFinance resolution, price history, and metrics, plus a DDGS news search wrapper. The frontend continues to call AgentOS at `POST /agents/groq-finance-agent/runs` using multipart form data.

## References

1. [Agno Groq provider overview](https://docs.agno.com/models/providers/gateways/groq/overview)
2. [Groq’s Agno integration guide](https://console.groq.com/docs/agno)
3. [Groq GPT-OSS 120B model documentation](https://console.groq.com/docs/model/openai/gpt-oss-120b)
4. [Groq supported models](https://console.groq.com/docs/models)
