from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "status": False,
            "message": "An error occurred.",
            "errors": {},
        }

        if hasattr(response, "data"):
            data = response.data
            if isinstance(data, dict):
                if "detail" in data:
                    error_data["message"] = str(data["detail"])
                else:
                    error_data["errors"] = data
                    error_data["message"] = "Validation error."
            elif isinstance(data, list):
                error_data["errors"] = {"non_field_errors": data}
                error_data["message"] = str(data[0]) if data else "Error."

        response.data = error_data
    else:
        logger.exception("Unhandled exception: %s", exc)
        response = Response(
            {"status": False, "message": "Internal server error.", "errors": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
