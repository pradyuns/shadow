import math

from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        limit: int | None = Query(None, ge=1, le=100, description="Alias for per_page"),
    ):
        # Query(...) defaults are Param objects outside FastAPI DI; unwrap them for direct instantiation/tests.
        resolved_page = getattr(page, "default", page)
        resolved_per_page = getattr(per_page, "default", per_page)
        resolved_limit = getattr(limit, "default", limit)

        self.page = max(1, int(resolved_page))
        requested_per_page = resolved_limit if resolved_limit is not None else resolved_per_page
        self.per_page = min(100, max(1, int(requested_per_page)))
        self.offset = (self.page - 1) * self.per_page

    def paginate(self, items: list, total: int) -> dict:
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": math.ceil(total / self.per_page) if self.per_page else 0,
        }
