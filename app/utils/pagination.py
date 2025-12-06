"""
Unified pagination handler supporting multiple pagination strategies.
Adapted from Django REST Framework for Flask with SQLAlchemy.
"""
from flask import Response, request
from sqlalchemy.orm import Query
from typing import Optional, Any
from .response import UnifiedResponse


class UnifiedPagination:
    """
    Unified pagination handler supporting multiple pagination strategies.

    Supports:
    - Page number based pagination (1, 2, 3, ...)
    - Limit/Offset based pagination (SQL-style)
    """

    @staticmethod
    def paginate_by_page(
        queryset: Query,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        serializer_func=None,
        message: str = "Success"
    ) -> tuple[Response, int]:
        """
        Page number based pagination (1, 2, 3, ...).

        Args:
            queryset: SQLAlchemy Query object to paginate
            page: Page number (defaults to query param 'page' or 1)
            page_size: Items per page (defaults to query param 'page_size' or 10)
            serializer_func: Function to serialize each item (e.g., item.serialize())
            message: Success message

        Returns:
            Tuple of (Response, status_code) from UnifiedResponse

        Example:
            queryset = Product.query
            return UnifiedPagination.paginate_by_page(
                queryset=queryset,
                serializer_func=lambda item: item.serialize(),
                message="Products retrieved successfully"
            )
        """
        # Get pagination parameters from query params or use defaults
        page = page or int(request.args.get('page', 1))
        page_size = page_size or int(request.args.get('page_size', 10))

        # Ensure page is at least 1
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Cap at 100 items per page

        # Get total count
        total_items = queryset.count()
        total_pages = (total_items + page_size - 1) // page_size  # Ceiling division

        # Calculate offset
        offset = (page - 1) * page_size

        # Get paginated items
        items = queryset.limit(page_size).offset(offset).all()

        # Serialize data if serializer provided
        if serializer_func:
            serialized_data = [serializer_func(item) for item in items]
        else:
            # Assume items have a serialize method
            serialized_data = [item.serialize() if hasattr(item, 'serialize') else item for item in items]

        # Calculate pagination metadata
        has_next = page < total_pages
        has_previous = page > 1

        return UnifiedResponse.success(
            data=serialized_data,
            message=message,
            meta={
                "pagination": {
                    "type": "page",
                    "current_page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_previous": has_previous,
                    "next_page": page + 1 if has_next else None,
                    "previous_page": page - 1 if has_previous else None
                }
            }
        )

    @staticmethod
    def paginate_by_limit_offset(
        queryset: Query,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        serializer_func=None,
        message: str = "Success"
    ) -> tuple[Response, int]:
        """
        Limit/Offset based pagination (SQL-style).

        Args:
            queryset: SQLAlchemy Query object to paginate
            limit: Number of items to return (defaults to query param 'limit' or 10)
            offset: Starting position (defaults to query param 'offset' or 0)
            serializer_func: Function to serialize each item
            message: Success message

        Returns:
            Tuple of (Response, status_code) from UnifiedResponse

        Example:
            queryset = Order.query.filter_by(user_id=current_user.id)
            return UnifiedPagination.paginate_by_limit_offset(
                queryset=queryset,
                serializer_func=lambda item: item.serialize(),
                message="Orders retrieved successfully"
            )
        """
        # Get pagination parameters from query params or use defaults
        limit = limit or int(request.args.get('limit', 10))
        offset = offset or int(request.args.get('offset', 0))

        # Ensure valid values
        limit = max(1, min(limit, 100))  # Cap at 100 items
        offset = max(0, offset)

        # Get total count
        total_count = queryset.count()

        # Get paginated items
        items = queryset.limit(limit).offset(offset).all()

        # Serialize data if serializer provided
        if serializer_func:
            serialized_data = [serializer_func(item) for item in items]
        else:
            # Assume items have a serialize method
            serialized_data = [item.serialize() if hasattr(item, 'serialize') else item for item in items]

        # Calculate pagination metadata
        has_next = offset + limit < total_count
        has_previous = offset > 0
        next_offset = offset + limit if has_next else None
        previous_offset = max(0, offset - limit) if has_previous else None

        return UnifiedResponse.success(
            data=serialized_data,
            message=message,
            meta={
                "pagination": {
                    "type": "limit_offset",
                    "limit": limit,
                    "offset": offset,
                    "total_items": total_count,
                    "returned_items": len(serialized_data),
                    "next_offset": next_offset,
                    "previous_offset": previous_offset,
                    "has_next": has_next,
                    "has_previous": has_previous
                }
            }
        )

    @staticmethod
    def paginate_by_count(
        queryset: Query,
        count: int,
        serializer_func=None,
        message: str = "Success"
    ) -> tuple[Response, int]:
        """
        Simple count-based pagination (just return first N items).
        Useful for "top N" queries.

        Args:
            queryset: SQLAlchemy Query object to paginate
            count: Number of items to return
            serializer_func: Function to serialize each item
            message: Success message

        Returns:
            Tuple of (Response, status_code) from UnifiedResponse
        """
        # Ensure valid count
        count = max(1, min(count, 100))  # Cap at 100 items

        # Get total count
        total_count = queryset.count()

        # Get limited items
        items = queryset.limit(count).all()

        # Serialize data if serializer provided
        if serializer_func:
            serialized_data = [serializer_func(item) for item in items]
        else:
            serialized_data = [item.serialize() if hasattr(item, 'serialize') else item for item in items]

        return UnifiedResponse.success(
            data=serialized_data,
            message=message,
            meta={
                "pagination": {
                    "type": "count",
                    "returned_items": len(serialized_data),
                    "total_items": total_count,
                    "has_more": total_count > count
                }
            }
        )
