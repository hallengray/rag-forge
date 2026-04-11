"""Tests for JSONL and golden set input loading."""

import json
from pathlib import Path

from rag_forge_evaluator.engine import EvaluationSample
from rag_forge_evaluator.input_loader import InputLoader


class TestLoadJsonl:
    def test_loads_valid_jsonl(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "telemetry.jsonl"
        lines = [
            {"query": "What is Python?", "contexts": ["Python is a language."], "response": "Python is a programming language."},
            {"query": "What is Rust?", "contexts": ["Rust is fast."], "response": "Rust is a systems language."},
        ]
        jsonl.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
        samples = InputLoader.load_jsonl(jsonl)
        assert len(samples) == 2
        assert isinstance(samples[0], EvaluationSample)
        assert samples[0].query == "What is Python?"

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "bad.jsonl"
        jsonl.write_text(
            '{"query": "ok", "contexts": ["c"], "response": "r"}\nnot valid json\n{"query": "also ok", "contexts": ["c2"], "response": "r2"}\n',
            encoding="utf-8",
        )
        assert len(InputLoader.load_jsonl(jsonl)) == 2

    def test_skips_lines_missing_required_fields(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "partial.jsonl"
        jsonl.write_text(
            '{"query": "q", "contexts": ["c"], "response": "r"}\n{"query": "missing response", "contexts": ["c"]}\n',
            encoding="utf-8",
        )
        assert len(InputLoader.load_jsonl(jsonl)) == 1

    def test_optional_fields_populated(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "full.jsonl"
        jsonl.write_text(
            json.dumps({"query": "q", "contexts": ["c"], "response": "r", "expected_answer": "expected", "chunk_ids": ["chunk_1"]}),
            encoding="utf-8",
        )
        samples = InputLoader.load_jsonl(jsonl)
        assert samples[0].expected_answer == "expected"
        assert samples[0].chunk_ids == ["chunk_1"]

    def test_empty_file(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("", encoding="utf-8")
        assert InputLoader.load_jsonl(jsonl) == []


class TestLoadGoldenSet:
    def test_loads_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "golden.json"
        gs.write_text(json.dumps([{"query": "What is RAG?", "expected_answer_keywords": ["retrieval", "augmented"], "difficulty": "easy", "topic": "general"}]), encoding="utf-8")
        samples = InputLoader.load_golden_set(gs)
        assert len(samples) == 1
        assert samples[0].query == "What is RAG?"
        assert samples[0].expected_answer == "retrieval, augmented"
        assert samples[0].contexts == []
        assert samples[0].response == ""

    def test_empty_golden_set(self, tmp_path: Path) -> None:
        gs = tmp_path / "empty.json"
        gs.write_text("[]", encoding="utf-8")
        assert InputLoader.load_golden_set(gs) == []
