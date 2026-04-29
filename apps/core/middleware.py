import logging
import time

logger = logging.getLogger("request")


class RequestLoggingMiddleware:
    """Log all incoming requests with duration."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = (time.time() - start) * 1000
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        return response
