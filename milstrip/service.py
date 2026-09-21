from __future__ import annotations

from milstrip.canonical.builder import build_canonical
from milstrip.domain import Record
from milstrip.intake.extractor import extract_candidates
from milstrip.parsing.normalizer import normalize_candidate
from milstrip.parsing.parser import parse_fields
from milstrip.validation.structural import validate_record


def process_text(text: str) -> list[Record]:
    records: list[Record] = []
    for _, candidate in extract_candidates(text):
        normalized, normalization_issue = normalize_candidate(candidate)
        fields = parse_fields(normalized)
        issues = validate_record(normalized, fields)
        if normalization_issue is not None:
            issues.append(normalization_issue)
        errors = [issue for issue in issues if issue.severity == "ERROR"]
        canonical = None if errors else build_canonical(fields)
        status = "REJECTED" if errors else ("REQUIRES_REVIEW" if issues else "VALID")
        records.append(Record(status, fields, tuple(issues), canonical))
    return records