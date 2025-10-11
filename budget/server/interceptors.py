"""gRPC interceptors for logging, error handling, and request validation.

This module provides interceptors that can be added to the gRPC server to handle
cross-cutting concerns like logging, error handling, and metrics.
"""

import time
from typing import Any, Callable

import grpc
from loguru import logger


class LoggingInterceptor(grpc.ServerInterceptor):
    """gRPC interceptor for logging all requests and responses.

    Logs the method name, request details, response status, and execution time
    for all gRPC calls.
    """

    def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept the service call to add logging.

        Args:
            continuation: Function to invoke to continue the RPC.
            handler_call_details: Details about the RPC call.

        Returns:
            RpcMethodHandler with logging wrapper.
        """
        method = handler_call_details.method

        def wrapper(behavior: Callable) -> Callable:
            def new_behavior(request: Any, context: grpc.ServicerContext) -> Any:
                start_time = time.time()
                logger.debug(f"gRPC call started: {method}")

                try:
                    response = behavior(request, context)
                    duration = time.time() - start_time
                    logger.info(
                        f"gRPC call completed: {method} - Duration: {duration:.3f}s"
                    )
                    return response
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        f"gRPC call failed: {method} - "
                        f"Error: {str(e)} - "
                        f"Duration: {duration:.3f}s",
                        exc_info=True,
                    )
                    raise

            return new_behavior

        return _wrap_rpc_behavior(continuation(handler_call_details), wrapper)


class ErrorHandlingInterceptor(grpc.ServerInterceptor):
    """gRPC interceptor for consistent error handling.

    Catches exceptions and converts them to appropriate gRPC status codes
    with meaningful error messages.
    """

    def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept the service call to add error handling.

        Args:
            continuation: Function to invoke to continue the RPC.
            handler_call_details: Details about the RPC call.

        Returns:
            RpcMethodHandler with error handling wrapper.
        """
        from budget.domain.exceptions import DatabaseError, ValidationError

        def wrapper(behavior: Callable) -> Callable:
            def new_behavior(request: Any, context: grpc.ServicerContext) -> Any:
                try:
                    return behavior(request, context)
                except ValidationError as e:
                    logger.warning(
                        f"Validation error in {handler_call_details.method}: {e}"
                    )
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details(f"Validation error: {str(e)}")
                    return None
                except DatabaseError as e:
                    logger.error(
                        f"Database error in {handler_call_details.method}: {e}"
                    )
                    context.set_code(grpc.StatusCode.INTERNAL)
                    context.set_details(f"Database error: {str(e)}")
                    return None
                except ValueError as e:
                    logger.warning(f"Value error in {handler_call_details.method}: {e}")
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details(f"Invalid value: {str(e)}")
                    return None
                except Exception as e:
                    logger.error(
                        f"Unexpected error in {handler_call_details.method}: {e}",
                        exc_info=True,
                    )
                    context.set_code(grpc.StatusCode.UNKNOWN)
                    context.set_details(f"Internal server error: {str(e)}")
                    return None

            return new_behavior

        return _wrap_rpc_behavior(continuation(handler_call_details), wrapper)


class MetricsInterceptor(grpc.ServerInterceptor):
    """gRPC interceptor for collecting request metrics.

    Tracks request counts, error rates, and response times for monitoring.
    """

    def __init__(self):
        """Initialize the metrics interceptor."""
        self.request_count = {}
        self.error_count = {}
        self.total_duration = {}

    def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept the service call to collect metrics.

        Args:
            continuation: Function to invoke to continue the RPC.
            handler_call_details: Details about the RPC call.

        Returns:
            RpcMethodHandler with metrics collection wrapper.
        """
        method = handler_call_details.method

        def wrapper(behavior: Callable) -> Callable:
            def new_behavior(request: Any, context: grpc.ServicerContext) -> Any:
                start_time = time.time()

                # Increment request count
                self.request_count[method] = self.request_count.get(method, 0) + 1

                try:
                    response = behavior(request, context)
                    return response
                except Exception:
                    # Increment error count
                    self.error_count[method] = self.error_count.get(method, 0) + 1
                    raise
                finally:
                    # Track duration
                    duration = time.time() - start_time
                    self.total_duration[method] = (
                        self.total_duration.get(method, 0.0) + duration
                    )

            return new_behavior

        return _wrap_rpc_behavior(continuation(handler_call_details), wrapper)

    def get_metrics(self) -> dict:
        """Get current metrics.

        Returns:
            dict: Dictionary containing request counts, error counts, and average durations.
        """
        metrics = {
            "requests": dict(self.request_count),
            "errors": dict(self.error_count),
            "avg_duration": {},
        }

        for method, total_time in self.total_duration.items():
            count = self.request_count.get(method, 1)
            metrics["avg_duration"][method] = total_time / count

        return metrics


def _wrap_rpc_behavior(
    handler: grpc.RpcMethodHandler, wrapper: Callable
) -> grpc.RpcMethodHandler:
    """Wrap RPC behavior with the given wrapper function.

    Args:
        handler: The RPC method handler to wrap.
        wrapper: Function to wrap the behavior with.

    Returns:
        RpcMethodHandler: New handler with wrapped behavior.
    """
    if handler is None:
        return None

    if handler.unary_unary:
        return grpc.unary_unary_rpc_method_handler(
            wrapper(handler.unary_unary),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    elif handler.unary_stream:
        return grpc.unary_stream_rpc_method_handler(
            wrapper(handler.unary_stream),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    elif handler.stream_unary:
        return grpc.stream_unary_rpc_method_handler(
            wrapper(handler.stream_unary),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    elif handler.stream_stream:
        return grpc.stream_stream_rpc_method_handler(
            wrapper(handler.stream_stream),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    return handler
