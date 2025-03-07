from prometheus_client import Counter, Histogram

class Metrics:
    def __init__(self, service_name):
        # Initialize Prometheus metrics with dynamic service name
        self.REQUEST_COUNT = Counter(
            f'{service_name}_api_requests_total', 
            f'Total API Requests for {service_name}', 
            ['method', 'endpoint']
        )
        self.REQUEST_LATENCY = Histogram(
            f'{service_name}_api_request_latency_seconds', 
            f'Request Latency for {service_name}', 
            ['endpoint']
        )
        self.ERROR_COUNT = Counter(
            f'{service_name}_api_errors_total', 
            f'Total API Errors for {service_name}', 
            ['endpoint', 'error_type']
        )

    def track_request(self, method, endpoint):
        self.REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()

    def track_error(self, endpoint, error_type):
        self.ERROR_COUNT.labels(endpoint=endpoint, error_type=error_type).inc()

    def track_latency(self, endpoint):
        return self.REQUEST_LATENCY.labels(endpoint=endpoint).time()
