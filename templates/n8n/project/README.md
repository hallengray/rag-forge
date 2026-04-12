# RAG-Forge n8n Integration

Connect n8n's AI Agent to RAG-Forge via MCP for automated document Q&A, ingestion, and evaluation.

## Prerequisites

- [n8n](https://n8n.io/) installed (self-hosted or cloud)
- RAG-Forge installed with documents indexed

## Setup

### 1. Start RAG-Forge MCP Server

```bash
rag-forge serve --mcp --transport http --port 3100
```

### 2. Import Workflow

1. Open n8n
2. Go to Workflows → Import from File
3. Select `workflow.json`

### 3. Configure

- Set `RAG_FORGE_MCP_URL` in n8n (default: `http://localhost:3100/sse`)
- Configure your LLM provider in the AI Agent node

### 4. Available MCP Tools

| Tool | Description |
|------|------------|
| `rag_query` | Execute a RAG query |
| `rag_audit` | Run evaluation audit |
| `rag_ingest` | Index documents |
| `rag_inspect` | Look up a chunk by ID |
| `rag_status` | Check pipeline health |
