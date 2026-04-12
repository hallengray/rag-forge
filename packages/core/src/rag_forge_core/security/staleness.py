"""Staleness checking: detect outdated context in retrieved chunks."""

import time
from dataclasses import dataclass, field


@dataclass
class StalenessResult:
    passed: bool
    stale_sources: list[str] = field(default_factory=list)
    threshold_days: int = 90


class StalenessChecker:
    def __init__(self, threshold_days: int = 90) -> None:
        self._threshold_days = threshold_days

    def check(self, contexts_metadata: list[dict[str, str | int | float]]) -> StalenessResult:
        if not contexts_metadata:
            return StalenessResult(passed=True, threshold_days=self._threshold_days)

        cutoff = time.time() - (self._threshold_days * 86400)
        stale_reported: list[str] = []
        # Only indexed_at drives the majority-stale pass/fail decision.
        # last_modified is surfaced as a warning in stale_sources but does not
        # contribute to the failure threshold (it is a softer, informational signal).
        indexed_at_stale_count = 0
        indexed_at_total = 0

        for meta in contexts_metadata:
            source = str(meta.get("source_document", "unknown"))
            indexed_at = meta.get("indexed_at")
            last_modified = meta.get("last_modified")

            if indexed_at is not None:
                indexed_at_total += 1
                if float(indexed_at) < cutoff:
                    indexed_at_stale_count += 1
                    stale_reported.append(source)
            elif last_modified is not None:
                # Surface as stale for observability, but do not count toward failure.
                if float(last_modified) < cutoff:
                    stale_reported.append(source)

        if indexed_at_total == 0:
            majority_stale = False
        else:
            majority_stale = indexed_at_stale_count > indexed_at_total / 2

        return StalenessResult(
            passed=not majority_stale,
            stale_sources=stale_reported,
            threshold_days=self._threshold_days,
        )
