"""Tests for adversarial test runner."""

import json
from pathlib import Path

from rag_forge_core.security.adversarial import AdversarialResult, AdversarialRunner, load_corpus


class TestLoadCorpus:
    def test_load_builtin_corpus(self) -> None:
        prompts = load_corpus()
        assert len(prompts) > 30
        assert all("text" in p for p in prompts)
        assert all("category" in p for p in prompts)
        assert all("expected_blocked" in p for p in prompts)

    def test_load_with_user_extension(self, tmp_path: Path) -> None:
        user_file = tmp_path / "custom.json"
        user_file.write_text(json.dumps({
            "version": "1.0",
            "prompts": [
                {"text": "Custom attack", "category": "custom", "expected_blocked": True, "severity": "high"}
            ],
        }))
        prompts = load_corpus(user_corpus_path=str(user_file))
        assert any(p["text"] == "Custom attack" for p in prompts)
        assert len(prompts) > 30


class TestAdversarialRunner:
    def test_run_returns_result(self) -> None:
        runner = AdversarialRunner()
        result = runner.run()
        assert isinstance(result, AdversarialResult)
        assert result.total_tested > 0
        assert result.blocked >= 0
        assert 0.0 <= result.pass_rate <= 1.0

    def test_benign_prompts_not_blocked(self) -> None:
        runner = AdversarialRunner()
        result = runner.run()
        assert result.passed_through > 0

    def test_injection_prompts_blocked(self) -> None:
        runner = AdversarialRunner()
        result = runner.run()
        injection_cat = result.by_category.get("prompt-injection")
        assert injection_cat is not None
        assert injection_cat["blocked"] > 0

    def test_result_includes_failures(self) -> None:
        runner = AdversarialRunner()
        result = runner.run()
        for failure in result.failures:
            assert failure["expected_blocked"] is True

    def test_by_category_has_all_categories(self) -> None:
        runner = AdversarialRunner()
        result = runner.run()
        assert "prompt-injection" in result.by_category
        assert "benign" in result.by_category
