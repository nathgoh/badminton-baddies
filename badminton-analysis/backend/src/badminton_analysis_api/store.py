from __future__ import annotations

from .models import AnalysisRecord


class AnalysisStore:
    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}

    def save(self, record: AnalysisRecord) -> AnalysisRecord:
        self._records[record.analysis_id] = record
        return record

    def get(self, analysis_id: str) -> AnalysisRecord:
        return self._records[analysis_id]

    def list_records(self) -> list[AnalysisRecord]:
        return sorted(
            self._records.values(),
            key=lambda record: record.created_at,
            reverse=True,
        )

    def delete(self, analysis_id: str) -> None:
        del self._records[analysis_id]
