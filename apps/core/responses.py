from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    return Response({"status": True, "message": message, "data": data}, status=status_code)


def created_response(data=None, message="Created successfully"):
    return success_response(data, message, status.HTTP_201_CREATED)


def error_response(message="An error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"status": False, "message": message, "errors": errors or {}},
        status=status_code,
    )


def not_found_response(message="Not found"):
    return error_response(message, status_code=status.HTTP_404_NOT_FOUND)


def forbidden_response(message="Permission denied"):
    return error_response(message, status_code=status.HTTP_403_FORBIDDEN)
