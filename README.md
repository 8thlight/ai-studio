# AI Studio

A curated collection of AI-powered tools for lead generation, enrichment, and research.

**Bonus**: At the end, you’ll also find a showcase of personal projects from individual studio members.

## Projects

### MarketMuse

An AI-powered lead generation tool built with AutoGen that helps sales teams research potential leads and companies. The system uses multiple AI agents working together to generate comprehensive lead reports.

**Key Features:**
- Tool-enabled SDR Agent that performs Google searches to gather information
- Account Executive Agent that enriches lead reports with additional insights
- Support for both OpenAI and local LLMs through Ollama
- Command-line interface for easy use

[Learn more about MarketMuse](./marketmuse/README.md)

### Lead Enrichment

A specialized tool that enriches company data by determining company sizes using the Perplexity API with OpenAI validation.

**Key Features:**
- Dual AI Processing using Perplexity API and GPT-4
- Smart caching to avoid duplicate API calls
- Incremental processing with progress saving
- Data validation and standardization
- Robust error handling with fallback validation

[Learn more about Lead Enrichment](./lead_enrichment/README.md)

## Getting Started

Each project has its own setup instructions and requirements. Please refer to the individual project READMEs for specific setup and usage instructions.

## Technologies Used

- Python
- AutoGen
- OpenAI API
- Perplexity API
- Ollama (for local LLM hosting)
- Various Python libraries for data processing and API interaction

## Related Projects

Check out these additional AI projects for more examples and inspiration:

### By Travis

- [AI Operator](https://github.com/T-rav/ai-operator) - A real-time voice conversation system with GPT-4o that features low-latency responses and natural interruption handling
- [Insight Mesh](https://github.com/T-rav/insight-mesh) - A complete RAG (Retrieval Augmented Generation) stack that helps organizations unlock the value of their internal knowledge

### By Ismail
- [AI Studio K8s](https://github.com/8thlight/ai-studio-k8s) - Kubernetes deployment configuration for AI Studio (private repository - contact Ismail for access)

## License

This repository is for demonstration and development purposes. 
