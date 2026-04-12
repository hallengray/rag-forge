"""Tests for n8n workflow export."""

import json

from rag_forge_core.n8n_export import generate_n8n_workflow


class TestN8NExport:
    def test_generates_valid_structure(self) -> None:
        workflow = generate_n8n_workflow(mcp_url="http://localhost:3100/sse")
        assert "nodes" in workflow
        assert "connections" in workflow
        assert len(workflow["nodes"]) == 4

    def test_contains_webhook_trigger(self) -> None:
        workflow = generate_n8n_workflow(mcp_url="http://localhost:3100/sse")
        node_types = [n["type"] for n in workflow["nodes"]]
        assert any("webhook" in t.lower() for t in node_types)

    def test_contains_mcp_url(self) -> None:
        url = "http://my-server:3100/sse"
        workflow = generate_n8n_workflow(mcp_url=url)
        assert url in json.dumps(workflow)

    def test_custom_workflow_name(self) -> None:
        workflow = generate_n8n_workflow(workflow_name="My Custom Pipeline")
        assert workflow["name"] == "My Custom Pipeline"

    def test_connections_reference_valid_nodes(self) -> None:
        workflow = generate_n8n_workflow()
        node_names = {n["name"] for n in workflow["nodes"]}
        for source_name in workflow["connections"]:
            assert source_name in node_names, f"Connection source '{source_name}' not in nodes"

    def test_default_settings(self) -> None:
        workflow = generate_n8n_workflow()
        assert workflow["settings"]["executionOrder"] == "v1"
