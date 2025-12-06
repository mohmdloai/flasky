"""
Unified response handler for consistent API responses across the application.

"""
from flask import jsonify, Response
from typing import Any, Optional, Dict


class UnifiedResponse:
    """
    Unified response handler for consistent API responses.

    All responses follow the format:
    {
        "success": bool,
        "message": str,
        "data": Any (optional),
        "meta": Dict (optional),
        "errors": Any (optional),
        "error_code": str (optional)
    }
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        meta: Optional[Dict] = None
    ) -> tuple[Response, int]:
        """
        Return a successful response.

        Args:
            data: The response data
            message: Success message
            status_code: HTTP status code
            meta: Additional metadata (pagination, etc.)

        Returns:
            Tuple of (Response, status_code)
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data
        }

        if meta:
            response_data["meta"] = meta

        return jsonify(response_data), status_code

    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: Optional[Any] = None,
        status_code: int = 400,
        error_code: Optional[str] = None
    ) -> tuple[Response, int]:
        """
        Return an error response.

        Args:
            message: Error message
            errors: Detailed error information
            status_code: HTTP status code
            error_code: Custom error code for frontend handling

        Returns:
            Tuple of (Response, status_code)
        """
        response_data = {
            "success": False,
            "message": message
        }

        if errors:
            response_data["errors"] = errors

        if error_code:
            response_data["error_code"] = error_code

        return jsonify(response_data), status_code

    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully",
        resource_id: Optional[Any] = None
    ) -> tuple[Response, int]:
        """
        Return a response for successfully created resources.

        Args:
            data: The created resource data
            message: Success message
            resource_id: ID of the created resource

        Returns:
            Tuple of (Response, status_code)
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data
        }

        if resource_id:
            response_data["resource_id"] = resource_id

        return jsonify(response_data), 201

    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> tuple[Response, int]:
        """
        Return a response for successfully deleted resources.

        Args:
            message: Success message

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({
            "success": True,
            "message": message
        }), 200

    @staticmethod
    def no_content() -> tuple[Response, int]:
        """
        Return a no content response.

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({}), 204

    @staticmethod
    def validation_error(errors: Dict) -> tuple[Response, int]:
        """
        Handle validation errors.

        Args:
            errors: Dictionary of validation errors

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({
            "success": False,
            "message": "Validation failed",
            "errors": errors
        }), 422

    @staticmethod
    def unauthorized(message: str = "Unauthorized access") -> tuple[Response, int]:
        """
        Handle unauthorized access.

        Args:
            message: Error message

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({
            "success": False,
            "message": message,
            "error_code": "UNAUTHORIZED"
        }), 401

    @staticmethod
    def forbidden(message: str = "Forbidden - insufficient permissions") -> tuple[Response, int]:
        """
        Handle forbidden access.

        Args:
            message: Error message

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({
            "success": False,
            "message": message,
            "error_code": "FORBIDDEN"
        }), 403

    @staticmethod
    def not_found(message: str = "Resource not found") -> tuple[Response, int]:
        """
        Handle not found errors.

        Args:
            message: Error message

        Returns:
            Tuple of (Response, status_code)
        """
        return jsonify({
            "success": False,
            "message": message,
            "error_code": "NOT_FOUND"
        }), 404
