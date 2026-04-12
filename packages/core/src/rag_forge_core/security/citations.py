"""Citation validation: verify response citations reference valid sources."""

import re
from dataclasses import dataclass, field


@dataclass
class CitationValidationResult:
    passed: bool
    total_citations: int
    valid_citations: int
    invalid_citations: list[str] = field(default_factory=list)


class CitationValidator:
    def __init__(self, citation_pattern: str = r"\[Source \d+\]") -> None:
        self._pattern = re.compile(citation_pattern)
        self._number_pattern = re.compile(r"\d+")

    def check(self, response: str, valid_source_count: int) -> CitationValidationResult:
        matches = self._pattern.findall(response)
        if not matches:
            return CitationValidationResult(passed=True, total_citations=0, valid_citations=0)

        valid = 0
        invalid: list[str] = []
        for citation in matches:
            number_match = self._number_pattern.search(citation)
            if number_match:
                num = int(number_match.group())
                if 1 <= num <= valid_source_count:
                    valid += 1
                else:
                    invalid.append(citation)
            else:
                invalid.append(citation)

        return CitationValidationResult(
            passed=len(invalid) == 0,
            total_citations=len(matches),
            valid_citations=valid,
            invalid_citations=invalid,
        )
