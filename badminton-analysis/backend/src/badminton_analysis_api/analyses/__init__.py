from .progress import ANALYZING_PROGRESS_STEPS

__all__ = [
    "ANALYZING_PROGRESS_STEPS",
    "AnalysisService",
    "AnalysisStore",
]


def __getattr__(name: str) -> object:
    if name == "AnalysisService":
        from .service import AnalysisService

        return AnalysisService
    if name == "AnalysisStore":
        from .store import AnalysisStore

        return AnalysisStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
