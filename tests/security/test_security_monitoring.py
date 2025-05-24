"""Security monitoring and logging tests.

This module contains tests for security monitoring, logging, and alerting features.
It verifies the implementation of security event collection, analysis, and response
mechanisms across the application infrastructure.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
from elasticsearch import Elasticsearch
from opensearch_py import OpenSearch
from prometheus_client import CollectorRegistry, Counter, Gauge
from services.audit import AuditService
from services.monitoring import MonitoringService
from services.security import SecurityException, SecurityService

from tests.security.config import get_security_config


@pytest.mark.security
@pytest.mark.monitoring
class TestSecurityEventMonitoring:
    """Test security event monitoring features.

    This test suite verifies the collection, processing, and analysis of security
    events across the application. It ensures that security events are properly
    captured, stored, and analyzed for potential threats.
    """

    def test_security_event_collection(self, security_test_client, security_config):
        """Test security event collection and processing.

        This test verifies:
        - Event collection from various sources
        - Event normalization and enrichment
        - Event storage and indexing
        - Event correlation
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Test event collection
        test_events = [
            {
                "type": "auth_failure",
                "source": "api",
                "timestamp": datetime.now().isoformat(),
                "user_id": "test_user",
                "ip_address": "192.168.1.1",
                "details": {"attempts": 5, "reason": "invalid_credentials"},
            },
            {
                "type": "file_access",
                "source": "storage",
                "timestamp": datetime.now().isoformat(),
                "user_id": "test_user",
                "file_path": "/sensitive/data.txt",
                "action": "read",
            },
            {
                "type": "config_change",
                "source": "system",
                "timestamp": datetime.now().isoformat(),
                "user_id": "admin",
                "change_type": "security_settings",
                "details": {"setting": "password_policy", "value": "updated"},
            },
        ]

        # Collect events
        for event in test_events:
            monitoring_service.collect_event(event)

        # Verify event collection
        collected_events = monitoring_service.get_recent_events(
            event_types=["auth_failure", "file_access", "config_change"],
            time_window=timedelta(minutes=5),
        )

        assert len(collected_events) == len(test_events)
        assert all(
            event["type"] in ["auth_failure", "file_access", "config_change"]
            for event in collected_events
        )

        # Test event correlation
        correlated_events = monitoring_service.correlate_events(collected_events)
        assert any(
            correlation["type"] == "potential_brute_force"
            for correlation in correlated_events
        )

    def test_security_metrics(self, security_test_client, security_config):
        """Test security metrics collection and monitoring.

        This test verifies:
        - Metric collection
        - Metric aggregation
        - Alert thresholds
        - Metric visualization
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Initialize metrics
        registry = CollectorRegistry()
        auth_failures = Counter(
            "security_auth_failures_total",
            "Total authentication failures",
            ["user_id", "source"],
            registry=registry,
        )
        file_accesses = Counter(
            "security_file_accesses_total",
            "Total file access attempts",
            ["user_id", "file_type", "action"],
            registry=registry,
        )
        security_score = Gauge(
            "security_risk_score",
            "Current security risk score",
            ["component"],
            registry=registry,
        )

        # Record metrics
        auth_failures.labels(user_id="test_user", source="api").inc(5)
        file_accesses.labels(
            user_id="test_user", file_type="sensitive", action="read"
        ).inc(3)
        security_score.labels(component="authentication").set(0.8)

        # Verify metrics
        metrics = monitoring_service.get_metrics()
        assert metrics["security_auth_failures_total"] > 0
        assert metrics["security_file_accesses_total"] > 0
        assert 0 <= metrics["security_risk_score"] <= 1

    def test_security_logging(self, security_test_client, security_config):
        """Test security logging features.

        This test verifies:
        - Log collection
        - Log encryption
        - Log retention
        - Log analysis
        """
        client, _ = security_test_client()
        audit_service = AuditService()

        # Test log collection
        test_logs = [
            {
                "level": "WARNING",
                "timestamp": datetime.now().isoformat(),
                "component": "auth",
                "message": "Multiple failed login attempts",
                "context": {"user_id": "test_user", "ip": "192.168.1.1", "attempts": 5},
            },
            {
                "level": "INFO",
                "timestamp": datetime.now().isoformat(),
                "component": "access",
                "message": "File access granted",
                "context": {
                    "user_id": "test_user",
                    "file": "/sensitive/data.txt",
                    "permission": "read",
                },
            },
        ]

        # Collect logs
        for log in test_logs:
            audit_service.log_security_event(log)

        # Verify log collection
        collected_logs = audit_service.get_recent_logs(
            levels=["WARNING", "INFO"], time_window=timedelta(minutes=5)
        )

        assert len(collected_logs) == len(test_logs)
        assert all(log["level"] in ["WARNING", "INFO"] for log in collected_logs)

        # Test log encryption
        encrypted_logs = audit_service.get_encrypted_logs()
        assert all(log["encrypted"] for log in encrypted_logs)

        # Test log retention
        retention_status = audit_service.check_log_retention()
        assert retention_status["compliance"]
        assert retention_status["encryption_enabled"]
        assert retention_status["backup_enabled"]


@pytest.mark.security
@pytest.mark.monitoring
class TestSecurityAlerting:
    """Test security alerting features.

    This test suite verifies the alerting system's ability to detect, process,
    and respond to security events. It ensures that alerts are properly generated,
    prioritized, and acted upon.
    """

    def test_alert_generation(self, security_test_client, security_config):
        """Test security alert generation and processing.

        This test verifies:
        - Alert detection
        - Alert prioritization
        - Alert notification
        - Alert response
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Test alert conditions
        alert_conditions = [
            {"type": "brute_force", "threshold": 5, "window": "5m", "severity": "high"},
            {
                "type": "sensitive_access",
                "threshold": 1,
                "window": "1h",
                "severity": "critical",
            },
            {
                "type": "config_change",
                "threshold": 1,
                "window": "1h",
                "severity": "medium",
            },
        ]

        # Configure alerts
        for condition in alert_conditions:
            monitoring_service.configure_alert(condition)

        # Generate test events
        for _ in range(6):
            monitoring_service.collect_event(
                {
                    "type": "auth_failure",
                    "source": "api",
                    "timestamp": datetime.now().isoformat(),
                    "user_id": "test_user",
                    "ip_address": "192.168.1.1",
                }
            )

        # Verify alert generation
        alerts = monitoring_service.get_active_alerts()
        assert any(
            alert["type"] == "brute_force" and alert["severity"] == "high"
            for alert in alerts
        )

        # Test alert notification
        notifications = monitoring_service.get_alert_notifications()
        assert any(notif["alert_type"] == "brute_force" for notif in notifications)

        # Test alert response
        response = monitoring_service.handle_alert(alerts[0])
        assert response["status"] == "handled"
        assert response["action_taken"] in ["block_ip", "disable_account"]

    def test_alert_correlation(self, security_test_client, security_config):
        """Test security alert correlation and analysis.

        This test verifies:
        - Alert correlation
        - Pattern detection
        - Threat intelligence
        - Response automation
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Test alert correlation
        test_alerts = [
            {
                "type": "auth_failure",
                "severity": "medium",
                "timestamp": datetime.now().isoformat(),
                "source": "api",
                "details": {"user_id": "test_user", "attempts": 3},
            },
            {
                "type": "sensitive_access",
                "severity": "high",
                "timestamp": datetime.now().isoformat(),
                "source": "storage",
                "details": {"user_id": "test_user", "file": "/sensitive/data.txt"},
            },
            {
                "type": "config_change",
                "severity": "critical",
                "timestamp": datetime.now().isoformat(),
                "source": "system",
                "details": {"user_id": "test_user", "setting": "security_policy"},
            },
        ]

        # Correlate alerts
        correlated = monitoring_service.correlate_alerts(test_alerts)

        # Verify correlation
        assert any(
            correlation["type"] == "potential_breach" for correlation in correlated
        )
        assert any(correlation["confidence"] > 0.8 for correlation in correlated)

        # Test pattern detection
        patterns = monitoring_service.detect_patterns(correlated)
        assert any(pattern["type"] == "escalating_access" for pattern in patterns)

        # Test threat intelligence
        intelligence = monitoring_service.check_threat_intelligence(correlated)
        assert intelligence["threat_level"] in ["low", "medium", "high", "critical"]
        assert "recommended_actions" in intelligence


@pytest.mark.security
@pytest.mark.monitoring
class TestSecurityAnalytics:
    """Test security analytics features.

    This test suite verifies the security analytics system's ability to analyze
    security events, detect patterns, and provide insights for security
    improvement.
    """

    def test_security_analysis(self, security_test_client, security_config):
        """Test security event analysis and reporting.

        This test verifies:
        - Event analysis
        - Pattern detection
        - Risk assessment
        - Security reporting
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Test event analysis
        analysis_period = timedelta(days=7)
        events = monitoring_service.get_events_for_analysis(analysis_period)

        # Analyze events
        analysis = monitoring_service.analyze_security_events(events)

        # Verify analysis
        assert "risk_score" in analysis
        assert "threat_level" in analysis
        assert "patterns" in analysis
        assert "recommendations" in analysis

        # Test pattern detection
        patterns = monitoring_service.detect_security_patterns(events)
        assert any(
            pattern["type"]
            in ["brute_force", "data_exfiltration", "privilege_escalation"]
            for pattern in patterns
        )

        # Test risk assessment
        risk_assessment = monitoring_service.assess_security_risk(events)
        assert 0 <= risk_assessment["overall_risk"] <= 1
        assert "risk_factors" in risk_assessment
        assert "mitigation_suggestions" in risk_assessment

        # Test security reporting
        report = monitoring_service.generate_security_report(analysis_period)
        assert "executive_summary" in report
        assert "detailed_analysis" in report
        assert "recommendations" in report
        assert "compliance_status" in report

    def test_security_visualization(self, security_test_client, security_config):
        """Test security data visualization.

        This test verifies:
        - Data aggregation
        - Visualization generation
        - Dashboard updates
        - Report generation
        """
        client, _ = security_test_client()
        monitoring_service = MonitoringService()

        # Test data aggregation
        time_ranges = ["1h", "24h", "7d", "30d"]
        for time_range in time_ranges:
            aggregated_data = monitoring_service.aggregate_security_data(time_range)
            assert "event_counts" in aggregated_data
            assert "alert_counts" in aggregated_data
            assert "risk_trends" in aggregated_data

        # Test visualization generation
        visualizations = monitoring_service.generate_security_visualizations()
        assert "event_timeline" in visualizations
        assert "alert_distribution" in visualizations
        assert "risk_heatmap" in visualizations
        assert "threat_map" in visualizations

        # Test dashboard updates
        dashboard = monitoring_service.update_security_dashboard()
        assert "current_status" in dashboard
        assert "active_alerts" in dashboard
        assert "risk_indicators" in dashboard
        assert "compliance_status" in dashboard

        # Test report generation
        report = monitoring_service.generate_visualization_report()
        assert "summary_charts" in report
        assert "detailed_analysis" in report
        assert "recommendations" in report
        assert "export_formats" in report
