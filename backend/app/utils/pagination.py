import math

from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page

    def paginate(self, items: list, total: int) -> dict:
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": math.ceil(total / self.per_page) if self.per_page else 0,
        }
