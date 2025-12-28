from .context import BuildReason

class BuildStats:
    created: int = 0
    changed: int = 0
    unchanged: int = 0
    deleted: int = 0
    errors: int = 0
    draft: int = 0
    time_seconds: float = 0.0

    def summary(self, total_pages: int) -> str:
        if total_pages == 0:
            return "Nothing to do."

        status = (
            "Build finished with errors."
            if self.errors
            else "Build finished successfully."
        )
        lines = [
            status,
            f"Processed {total_pages} pages in {self.time_seconds:.2f}s.",
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

    def add_stat(self, build_reason: BuildReason):
        match build_reason:
            case BuildReason.CHANGED:
                self.changed += 1
            case BuildReason.UNCHANGED:
                self.unchanged += 1
            case BuildReason.CREATED:
                self.created += 1
            case BuildReason.DELETED:
                self.deleted += 1