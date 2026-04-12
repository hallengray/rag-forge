"""Generate importable n8n workflow JSON from pipeline configuration."""

from typing import Any


def generate_n8n_workflow(
    mcp_url: str = "http://localhost:3100/sse",
    workflow_name: str = "RAG-Forge Pipeline",
) -> dict[str, Any]:
    """Generate an n8n workflow JSON connecting to a RAG-Forge MCP server.

    The generated workflow contains four nodes:
    1. Webhook Trigger — accepts POST requests at /rag-query
    2. AI Agent — conversational agent that uses the MCP tool
    3. RAG-Forge MCP — connects to the RAG-Forge MCP server via SSE
    4. HTTP Response — returns the agent's output

    Args:
        mcp_url: The SSE endpoint of the RAG-Forge MCP server.
        workflow_name: Human-readable name for the workflow.

    Returns:
        A dict that can be serialized to JSON and imported into n8n.
    """
    return {
        "name": workflow_name,
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "rag-query",
                    "responseMode": "responseNode",
                },
                "id": "webhook-trigger",
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [250, 300],
            },
            {
                "parameters": {
                    "agent": "conversationalAgent",
                    "options": {
                        "systemMessage": (
                            "You are a RAG assistant. Use the rag_query tool to answer "
                            "questions based on the indexed document collection."
                        ),
                    },
                },
                "id": "ai-agent",
                "name": "AI Agent",
                "type": "@n8n/n8n-nodes-langchain.agent",
                "typeVersion": 1.7,
                "position": [470, 300],
            },
            {
                "parameters": {"sseEndpoint": mcp_url},
                "id": "mcp-tool",
                "name": "RAG-Forge MCP",
                "type": "@n8n/n8n-nodes-langchain.toolMcp",
                "typeVersion": 1,
                "position": [470, 500],
            },
            {
                "parameters": {
                    "respondWith": "text",
                    "responseBody": "={{ $json.output }}",
                },
                "id": "http-response",
                "name": "HTTP Response",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1,
                "position": [690, 300],
            },
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [[{"node": "AI Agent", "type": "main", "index": 0}]],
            },
            "AI Agent": {
                "main": [[{"node": "HTTP Response", "type": "main", "index": 0}]],
            },
            "RAG-Forge MCP": {
                "ai_tool": [[{"node": "AI Agent", "type": "ai_tool", "index": 0}]],
            },
        },
        "settings": {"executionOrder": "v1"},
    }
