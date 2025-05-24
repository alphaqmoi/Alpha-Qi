"""Test performance benchmarks and metrics."""

from collections import defaultdict

import pytest

from utils.exceptions import SecurityException


@pytest.fixture
def performance_test_client():
    """Fixture providing performance test client."""
    from utils.performance import PerformanceManager

    client = PerformanceManager()
    config = {
        "test_mode": True,
        "mock_services": True,
        "performance_features": [
            "load_testing",
            "stress_testing",
            "scalability_testing",
            "concurrent_testing",
        ],
    }
    return client, config


@pytest.mark.security
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Test performance benchmarks and metrics."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, performance_test_client):
        """Setup and teardown for each test."""
        self.service, self.config = performance_test_client
        self.metrics = defaultdict(list)
        yield
        self.cleanup()

    def cleanup(self):
        """Clean up test resources."""
        self.service.cleanup_performance_resources()
        self.service.reset_performance_state()

    def test_load_performance(self, performance_test_client, mock_security_services):
        """Test load performance benchmarks."""
        client, config = performance_test_client
        services = mock_security_services

        # Test normal load scenarios
        normal_load_tests = [
            {
                "scenario": "api_throughput",
                "load": {
                    "requests_per_second": 1000,
                    "duration": "5m",
                    "concurrent_users": 100,
                },
                "expected_metrics": {
                    "response_time_p95": 200,  # ms
                    "error_rate": 0.001,  # 0.1%
                    "throughput": 1000,  # req/s
                },
            },
            {
                "scenario": "data_processing",
                "load": {
                    "records_per_second": 10000,
                    "duration": "10m",
                    "batch_size": 1000,
                },
                "expected_metrics": {
                    "processing_time_p95": 500,  # ms
                    "error_rate": 0.0001,  # 0.01%
                    "throughput": 10000,  # records/s
                },
            },
            {
                "scenario": "event_processing",
                "load": {"events_per_second": 5000, "duration": "15m", "consumers": 10},
                "expected_metrics": {
                    "processing_time_p95": 100,  # ms
                    "error_rate": 0.0005,  # 0.05%
                    "throughput": 5000,  # events/s
                },
            },
        ]

        # Test peak load scenarios
        peak_load_tests = [
            {
                "scenario": "api_peak_load",
                "load": {
                    "requests_per_second": 5000,
                    "duration": "1m",
                    "concurrent_users": 500,
                },
                "expected_metrics": {
                    "response_time_p95": 500,  # ms
                    "error_rate": 0.01,  # 1%
                    "throughput": 5000,  # req/s
                },
            },
            {
                "scenario": "data_peak_load",
                "load": {
                    "records_per_second": 50000,
                    "duration": "2m",
                    "batch_size": 5000,
                },
                "expected_metrics": {
                    "processing_time_p95": 1000,  # ms
                    "error_rate": 0.001,  # 0.1%
                    "throughput": 50000,  # records/s
                },
            },
            {
                "scenario": "event_peak_load",
                "load": {"events_per_second": 25000, "duration": "3m", "consumers": 50},
                "expected_metrics": {
                    "processing_time_p95": 200,  # ms
                    "error_rate": 0.002,  # 0.2%
                    "throughput": 25000,  # events/s
                },
            },
        ]

        for test in normal_load_tests + peak_load_tests:
            result = services["performance"].test_load_performance(test)
            assert "metrics" in result
            assert "thresholds" in result
            assert "compliance" in result
            for metric, expected in test["expected_metrics"].items():
                assert result["metrics"][metric] <= expected

    def test_stress_performance(self, performance_test_client, mock_security_services):
        """Test stress performance benchmarks."""
        client, config = performance_test_client
        services = mock_security_services

        # Test resource stress scenarios
        resource_stress_tests = [
            {
                "scenario": "cpu_stress",
                "stress": {
                    "cpu_utilization": 0.9,  # 90%
                    "duration": "5m",
                    "cores": "all",
                },
                "expected_metrics": {
                    "response_time_p95": 1000,  # ms
                    "error_rate": 0.05,  # 5%
                    "throughput_degradation": 0.2,  # 20%
                },
            },
            {
                "scenario": "memory_stress",
                "stress": {
                    "memory_utilization": 0.9,  # 90%
                    "duration": "5m",
                    "allocation_rate": "high",
                },
                "expected_metrics": {
                    "response_time_p95": 800,  # ms
                    "error_rate": 0.03,  # 3%
                    "throughput_degradation": 0.15,  # 15%
                },
            },
            {
                "scenario": "io_stress",
                "stress": {
                    "io_utilization": 0.9,  # 90%
                    "duration": "5m",
                    "operation_rate": "high",
                },
                "expected_metrics": {
                    "response_time_p95": 1200,  # ms
                    "error_rate": 0.04,  # 4%
                    "throughput_degradation": 0.25,  # 25%
                },
            },
        ]

        # Test network stress scenarios
        network_stress_tests = [
            {
                "scenario": "bandwidth_stress",
                "stress": {
                    "bandwidth_utilization": 0.9,  # 90%
                    "duration": "5m",
                    "packet_size": "large",
                },
                "expected_metrics": {
                    "response_time_p95": 1500,  # ms
                    "error_rate": 0.06,  # 6%
                    "throughput_degradation": 0.3,  # 30%
                },
            },
            {
                "scenario": "latency_stress",
                "stress": {"latency": 500, "duration": "5m", "jitter": "high"},  # ms
                "expected_metrics": {
                    "response_time_p95": 2000,  # ms
                    "error_rate": 0.07,  # 7%
                    "throughput_degradation": 0.35,  # 35%
                },
            },
            {
                "scenario": "connection_stress",
                "stress": {
                    "connections": 10000,
                    "duration": "5m",
                    "connection_rate": "high",
                },
                "expected_metrics": {
                    "response_time_p95": 1800,  # ms
                    "error_rate": 0.08,  # 8%
                    "throughput_degradation": 0.4,  # 40%
                },
            },
        ]

        for test in resource_stress_tests + network_stress_tests:
            result = services["performance"].test_stress_performance(test)
            assert "metrics" in result
            assert "thresholds" in result
            assert "compliance" in result
            for metric, expected in test["expected_metrics"].items():
                assert result["metrics"][metric] <= expected

    def test_scalability_performance(
        self, performance_test_client, mock_security_services
    ):
        """Test scalability performance benchmarks."""
        client, config = performance_test_client
        services = mock_security_services

        # Test horizontal scaling scenarios
        horizontal_scaling_tests = [
            {
                "scenario": "service_scaling",
                "scaling": {
                    "initial_instances": 1,
                    "max_instances": 10,
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 300,  # seconds
                    "throughput_improvement": 0.8,  # 80%
                    "cost_efficiency": 0.7,  # 70%
                },
            },
            {
                "scenario": "database_scaling",
                "scaling": {
                    "initial_shards": 1,
                    "max_shards": 5,
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 600,  # seconds
                    "throughput_improvement": 0.6,  # 60%
                    "cost_efficiency": 0.8,  # 80%
                },
            },
            {
                "scenario": "cache_scaling",
                "scaling": {
                    "initial_nodes": 1,
                    "max_nodes": 8,
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 180,  # seconds
                    "throughput_improvement": 0.7,  # 70%
                    "cost_efficiency": 0.75,  # 75%
                },
            },
        ]

        # Test vertical scaling scenarios
        vertical_scaling_tests = [
            {
                "scenario": "compute_scaling",
                "scaling": {
                    "initial_cpu": 2,
                    "max_cpu": 16,
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 240,  # seconds
                    "throughput_improvement": 0.75,  # 75%
                    "cost_efficiency": 0.65,  # 65%
                },
            },
            {
                "scenario": "memory_scaling",
                "scaling": {
                    "initial_memory": "4GB",
                    "max_memory": "32GB",
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 300,  # seconds
                    "throughput_improvement": 0.7,  # 70%
                    "cost_efficiency": 0.7,  # 70%
                },
            },
            {
                "scenario": "storage_scaling",
                "scaling": {
                    "initial_storage": "100GB",
                    "max_storage": "1TB",
                    "scaling_factor": 2,
                    "duration": "30m",
                },
                "expected_metrics": {
                    "scaling_time": 360,  # seconds
                    "throughput_improvement": 0.65,  # 65%
                    "cost_efficiency": 0.85,  # 85%
                },
            },
        ]

        for test in horizontal_scaling_tests + vertical_scaling_tests:
            result = services["performance"].test_scalability_performance(test)
            assert "metrics" in result
            assert "thresholds" in result
            assert "compliance" in result
            for metric, expected in test["expected_metrics"].items():
                assert result["metrics"][metric] >= expected

    def test_concurrent_performance(
        self, performance_test_client, mock_security_services
    ):
        """Test concurrent performance benchmarks."""
        client, config = performance_test_client
        services = mock_security_services

        # Test concurrent user scenarios
        concurrent_user_tests = [
            {
                "scenario": "user_concurrency",
                "concurrency": {
                    "users": 1000,
                    "ramp_up_time": "5m",
                    "duration": "15m",
                    "think_time": "1s",
                },
                "expected_metrics": {
                    "response_time_p95": 500,  # ms
                    "error_rate": 0.01,  # 1%
                    "throughput": 100,  # req/s
                },
            },
            {
                "scenario": "session_concurrency",
                "concurrency": {
                    "sessions": 5000,
                    "ramp_up_time": "10m",
                    "duration": "30m",
                    "session_duration": "5m",
                },
                "expected_metrics": {
                    "response_time_p95": 800,  # ms
                    "error_rate": 0.02,  # 2%
                    "throughput": 200,  # req/s
                },
            },
            {
                "scenario": "transaction_concurrency",
                "concurrency": {
                    "transactions": 100,
                    "ramp_up_time": "2m",
                    "duration": "10m",
                    "transaction_time": "30s",
                },
                "expected_metrics": {
                    "response_time_p95": 2000,  # ms
                    "error_rate": 0.03,  # 3%
                    "throughput": 50,  # req/s
                },
            },
        ]

        # Test concurrent operation scenarios
        concurrent_operation_tests = [
            {
                "scenario": "read_concurrency",
                "concurrency": {
                    "operations": 10000,
                    "ramp_up_time": "5m",
                    "duration": "15m",
                    "operation_type": "read",
                },
                "expected_metrics": {
                    "response_time_p95": 100,  # ms
                    "error_rate": 0.001,  # 0.1%
                    "throughput": 1000,  # ops/s
                },
            },
            {
                "scenario": "write_concurrency",
                "concurrency": {
                    "operations": 5000,
                    "ramp_up_time": "5m",
                    "duration": "15m",
                    "operation_type": "write",
                },
                "expected_metrics": {
                    "response_time_p95": 200,  # ms
                    "error_rate": 0.002,  # 0.2%
                    "throughput": 500,  # ops/s
                },
            },
            {
                "scenario": "mixed_concurrency",
                "concurrency": {
                    "operations": 15000,
                    "ramp_up_time": "5m",
                    "duration": "15m",
                    "operation_type": "mixed",
                },
                "expected_metrics": {
                    "response_time_p95": 150,  # ms
                    "error_rate": 0.0015,  # 0.15%
                    "throughput": 1500,  # ops/s
                },
            },
        ]

        for test in concurrent_user_tests + concurrent_operation_tests:
            result = services["performance"].test_concurrent_performance(test)
            assert "metrics" in result
            assert "thresholds" in result
            assert "compliance" in result
            for metric, expected in test["expected_metrics"].items():
                assert result["metrics"][metric] <= expected
