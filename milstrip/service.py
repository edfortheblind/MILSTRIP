"""Phase 1 pipeline: raw text in, a list of fully-annotated MilstripRecord out.

RawInput -> CandidateMILSTRIP -> NormalizedMILSTRIP -> ParsedMILSTRIP ->
ValidatedMILSTRIP -> CanonicalMILSTRIP, per docs/MILSTRIP_SPEC.md § Raw input
model. Nothing in this module touches a database, a network, or the
filesystem beyond what the caller already handed it — see docs/ROADMAP.md
for where database validation (Phase 2) and submission (Phase 3) attach.
"""

from __future__ import annotations

from milstrip.canonical.builder import build_canonical
from milstrip.domain import MilstripRecord, ProcessingIssue
from milstrip.intake.extractor import extract_candidates
from milstrip.parsing.normalizer import normalize_line, placeholder_expansions
from milstrip.parsing.parser import parse_fields
from milstrip.validation.structural import validate_record


def process_text(raw_text: str) -> list[MilstripRecord]:
    records = []
    for raw_line, cleaned_line in extract_candidates(raw_text):
        normalized = normalize_line(cleaned_line)
        normalization_issues: list[ProcessingIssue] = []
        expansions = placeholder_expansions(normalized)
        has_placeholder_punctuation = "." in normalized or "…" in normalized
        if has_placeholder_punctuation and not expansions:
            normalization_issues.append(ProcessingIssue(
                code="MIL-NORM-002",
                message="Dot/ellipsis punctuation does not match the collected repair pattern. "
                        "The record was not altered; correct it manually or supply more evidence.",
                severity="ERROR",
            ))
        elif expansions:
            valid_expansions: list[str] = []
            for expansion in expansions:
                expansion_fields = parse_fields(expansion)
                expansion_issues = validate_record(expansion, expansion_fields)
                if not any(issue.severity == "ERROR" for issue in expansion_issues):
                    valid_expansions.append(expansion)
            if len(valid_expansions) == 1:
                normalized = valid_expansions[0]
                normalization_issues.append(ProcessingIssue(
                    code="MIL-NORM-001",
                    message="Dot/ellipsis spacing contamination was repaired using the only "
                            "interpretation that satisfies the fixed-width contract. Review the "
                            "canonical record before submission.",
                    severity="WARNING",
                ))
            else:
                reason = "no valid" if not valid_expansions else "multiple valid"
                normalization_issues.append(ProcessingIssue(
                    code="MIL-NORM-002",
                    message=f"Dot/ellipsis spacing is ambiguous ({reason} interpretations). "
                            "The record was not repaired; obtain clarification or correct it manually.",
                    severity="ERROR",
                ))

        record = MilstripRecord(raw_line=raw_line, cleaned_line=normalized)
        fields = parse_fields(normalized)
        record.fields = fields
        record.issues = normalization_issues + validate_record(normalized, fields)
        if not record.has_errors:
            record.canonical = build_canonical(fields)
        records.append(record)
    return records
