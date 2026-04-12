"""Tests for golden set management."""

import json
from pathlib import Path

import pytest

from rag_forge_evaluator.golden_set import GoldenSet, GoldenSetEntry


class TestGoldenSetLoad:
    def test_load_valid_file(self, tmp_path: Path) -> None:
        data = {
            "entries": [
                {"query": "What is RAG?", "expected_answer_keywords": ["retrieval", "augmented", "generation"]},
                {"query": "How does chunking work?", "expected_answer_keywords": ["split", "tokens"], "difficulty": "hard", "topic": "ingestion"},
            ]
        }
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(data))
        gs = GoldenSet()
        gs.load(path)
        assert len(gs.entries) == 2
        assert gs.entries[0].query == "What is RAG?"
        assert gs.entries[1].difficulty == "hard"

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        gs = GoldenSet()
        with pytest.raises(FileNotFoundError):
            gs.load(tmp_path / "missing.json")

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json")
        gs = GoldenSet()
        with pytest.raises(json.JSONDecodeError):
            gs.load(path)


class TestGoldenSetSave:
    def test_save_and_reload(self, tmp_path: Path) -> None:
        gs = GoldenSet()
        gs.entries = [GoldenSetEntry(query="What is RAG?", expected_answer_keywords=["retrieval", "generation"])]
        path = tmp_path / "golden.json"
        gs.save(path)
        gs2 = GoldenSet()
        gs2.load(path)
        assert len(gs2.entries) == 1
        assert gs2.entries[0].query == "What is RAG?"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        gs = GoldenSet()
        gs.entries = [GoldenSetEntry(query="Q1", expected_answer_keywords=["a"])]
        path = tmp_path / "subdir" / "golden.json"
        gs.save(path)
        assert path.exists()


class TestGoldenSetAdd:
    def test_add_entry(self) -> None:
        gs = GoldenSet()
        gs.add_entry(query="What is RAG?", expected_answer_keywords=["retrieval"])
        assert len(gs.entries) == 1
        assert gs.entries[0].query == "What is RAG?"

    def test_add_entry_with_all_fields(self) -> None:
        gs = GoldenSet()
        gs.add_entry(query="Complex?", expected_answer_keywords=["answer"], expected_source_chunk_ids=["chunk-1"], difficulty="hard", topic="science", requires_multi_hop=True, adversarial=True)
        entry = gs.entries[0]
        assert entry.difficulty == "hard"
        assert entry.requires_multi_hop is True
        assert entry.adversarial is True


class TestGoldenSetFromTraffic:
    def test_sample_from_jsonl(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "traffic.jsonl"
        lines = [
            json.dumps({"query": "What is RAG?", "contexts": ["ctx1"], "response": "RAG is..."}),
            json.dumps({"query": "How to chunk?", "contexts": ["ctx2"], "response": "Chunking is..."}),
            json.dumps({"query": "What is embedding?", "contexts": ["ctx3"], "response": "Embedding is..."}),
        ]
        jsonl_path.write_text("\n".join(lines))
        gs = GoldenSet()
        added = gs.add_from_traffic(jsonl_path, sample_size=2)
        assert added == 2
        assert len(gs.entries) == 2

    def test_sample_size_larger_than_traffic(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "traffic.jsonl"
        jsonl_path.write_text(json.dumps({"query": "Q1", "contexts": [], "response": "A1"}))
        gs = GoldenSet()
        added = gs.add_from_traffic(jsonl_path, sample_size=100)
        assert added == 1

    def test_empty_traffic_file(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "traffic.jsonl"
        jsonl_path.write_text("")
        gs = GoldenSet()
        added = gs.add_from_traffic(jsonl_path, sample_size=10)
        assert added == 0


class TestGoldenSetValidate:
    def test_empty_set_has_error(self) -> None:
        gs = GoldenSet()
        errors = gs.validate()
        assert any("empty" in e.lower() for e in errors)

    def test_valid_set_no_errors(self) -> None:
        gs = GoldenSet()
        gs.entries = [
            GoldenSetEntry(query="Q1", expected_answer_keywords=["a"]),
            GoldenSetEntry(query="Q2", expected_answer_keywords=["b"]),
        ]
        errors = gs.validate()
        assert len(errors) == 0

    def test_duplicate_queries_flagged(self) -> None:
        gs = GoldenSet()
        gs.entries = [
            GoldenSetEntry(query="Same question?", expected_answer_keywords=["a"]),
            GoldenSetEntry(query="Same question?", expected_answer_keywords=["b"]),
        ]
        errors = gs.validate()
        assert any("duplicate" in e.lower() for e in errors)

    def test_missing_keywords_flagged(self) -> None:
        gs = GoldenSet()
        gs.entries = [GoldenSetEntry(query="Q1", expected_answer_keywords=[])]
        errors = gs.validate()
        assert any("keyword" in e.lower() for e in errors)

    def test_topic_balance_warning(self) -> None:
        gs = GoldenSet()
        gs.entries = [GoldenSetEntry(query=f"Q{i}", expected_answer_keywords=["a"], topic="same") for i in range(10)]
        errors = gs.validate()
        assert any("topic" in e.lower() or "balance" in e.lower() for e in errors)
