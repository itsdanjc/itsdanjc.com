import time
from typing import Self
from .context import BuildReason

class BuildStats:
    """
    Class for storing build statistics.
    """
    created: int = 0
    changed: int = 0
    unchanged: int = 0
    deleted: int = 0
    errors: int = 0
    draft: int = 0
    validated: int = 0
    start_time: float
    end_time: float
    total_time_s: float

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.total_time_s = self.end_time - self.start_time


    def summary(self) -> str:
        total_pages = sum({
            self.created, self.changed,
             self.unchanged, self.deleted,
            self.validated, self.errors,
        })

        if total_pages == 0:
            return "Nothing to do."

        status = (
            "Build finished with errors."
            if self.errors
            else "Build finished successfully."
        )
        lines = [
            status,
            f"Processed {total_pages} pages in {self.total_time_s:.2f}s.",
        ]
        stats = [
            ("Created", self.created),
            ("Draft", self.draft),
            ("Changed", self.changed),
            ("Unchanged", self.unchanged),
            ("Deleted", self.deleted),
            ("Errors", self.errors),
        ]

        width = max(len(name) for name, _ in stats)
        for name, value in stats:
            if value:
                lines.append(f"  {name.ljust(width)} {value}")
        return "\n".join(lines)

    def add_stat(self, build_reason: BuildReason | int):
        if isinstance(build_reason, int):
            build_reason = BuildReason(build_reason)

        match build_reason:
            case BuildReason.CHANGED:
                self.changed += 1
            case BuildReason.UNCHANGED:
                self.unchanged += 1
            case BuildReason.CREATED:
                self.created += 1
            case BuildReason.DELETED:
                self.deleted += 1
            case BuildReason.VALIDATION:
                self.validated += 1