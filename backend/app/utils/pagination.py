import math

from fastapi import Query


# fastapi dependency that parses page/per_page from query params
class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        limit: int | None = Query(None, ge=1, le=100, description="Alias for per_page"),
    ):
        self.page = page
        self.per_page = limit if limit is not None else per_page
        self.offset = (page - 1) * self.per_page

    def paginate(self, items: list, total: int) -> dict:
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": math.ceil(total / self.per_page) if self.per_page else 0,
        }
