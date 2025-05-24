"""Security test configuration."""

import os
from datetime import timedelta
from typing import Any, Dict, List, Optional

# Base security configuration
SECURITY_CONFIG = {
    # Authentication settings
    "authentication": {
        "max_login_attempts": 5,
        "lockout_duration": timedelta(minutes=30),
        "password_policy": {
            "min_length": 12,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special": True,
            "prevent_reuse": 5,
            "expiry_days": 90,
        },
        "token": {
            "access_token_expiry": timedelta(minutes=15),
            "refresh_token_expiry": timedelta(days=7),
            "jwt_secret": os.getenv("JWT_SECRET", "your-secret-key"),
            "algorithm": "HS256",
        },
        "mfa": {
            "enabled": True,
            "methods": ["totp", "sms", "email"],
            "backup_codes": 10,
        },
    },
    # Authorization settings
    "authorization": {
        "roles": {
            "admin": {"permissions": ["*"], "description": "Full system access"},
            "user": {
                "permissions": ["read:own", "write:own", "delete:own"],
                "description": "Standard user access",
            },
            "guest": {
                "permissions": ["read:public"],
                "description": "Limited public access",
            },
        },
        "resource_access": {
            "enforce_ownership": True,
            "allow_sharing": True,
            "sharing_permissions": ["read", "write"],
            "group_permissions": True,
        },
    },
    # API security settings
    "api": {
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 100,
            "burst_limit": 50,
        },
        "cors": {
            "enabled": True,
            "allowed_origins": ["https://app.example.com"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
            "allowed_headers": ["Authorization", "Content-Type"],
            "max_age": 3600,
        },
        "validation": {
            "request_size_limit": "10MB",
            "require_https": True,
            "validate_content_type": True,
        },
        "headers": {
            "security_headers": {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
            }
        },
    },
    # Data security settings
    "data": {
        "encryption": {
            "algorithm": "AES-256-GCM",
            "key_rotation_days": 90,
            "secure_deletion": True,
        },
        "storage": {
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "backup_encryption": True,
        },
        "validation": {
            "sanitize_input": True,
            "validate_output": True,
            "prevent_sql_injection": True,
            "prevent_xss": True,
        },
        "retention": {
            "enabled": True,
            "default_period": timedelta(days=365),
            "compliance_periods": {
                "financial": timedelta(days=730),
                "medical": timedelta(days=2555),
            },
        },
    },
    # File security settings
    "file": {
        "upload": {
            "max_size": "100MB",
            "allowed_types": ["pdf", "doc", "docx", "txt", "jpg", "png"],
            "scan_malware": True,
            "validate_content": True,
        },
        "storage": {"encryption": True, "access_control": True, "versioning": True},
        "sharing": {
            "enabled": True,
            "expiry_days": 7,
            "require_password": True,
            "audit_logging": True,
        },
    },
    # Network security settings
    "network": {
        "ssl": {
            "min_version": "TLSv1.2",
            "preferred_ciphers": [
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES256-GCM-SHA384",
            ],
            "cert_validation": True,
        },
        "firewall": {
            "enabled": True,
            "default_policy": "deny",
            "allowed_ports": [80, 443],
            "ip_whitelist": ["10.0.0.0/8", "172.16.0.0/12"],
        },
        "dns": {
            "dnssec_enabled": True,
            "dns_over_https": True,
            "prevent_dns_leaks": True,
        },
        "ddos_protection": {
            "enabled": True,
            "rate_limiting": True,
            "blacklist_threshold": 1000,
        },
    },
    # Infrastructure security settings
    "infrastructure": {
        "network": {
            "segmentation": {
                "enabled": True,
                "environments": ["production", "staging", "development"],
                "isolation_rules": {
                    "production": {"isolated": True, "can_access_staging": False},
                    "staging": {"isolated": True, "can_access_production": False},
                    "development": {"isolated": True, "can_access_production": False},
                },
            },
            "load_balancer": {
                "ssl_termination_enabled": True,
                "health_check_enabled": True,
                "ddos_protection_enabled": True,
                "waf_enabled": True,
                "rate_limiting_enabled": True,
                "ip_whitelisting_enabled": True,
            },
        },
        "database": {
            "encryption": {
                "at_rest": True,
                "in_transit": True,
                "algorithm": "AES-256-GCM",
            },
            "access_control": {
                "enabled": True,
                "audit_logging_enabled": True,
                "connection_encryption_enabled": True,
                "backup_encryption_enabled": True,
            },
        },
        "cache": {
            "encryption": {"enabled": True, "algorithm": "AES-256-GCM"},
            "isolation": {
                "enabled": True,
                "public_access_disabled": True,
                "network_isolation_enabled": True,
            },
            "access_control": {"enabled": True, "audit_logging_enabled": True},
        },
        "queue": {
            "encryption": {"enabled": True, "algorithm": "AES-256-GCM"},
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "features": {
                "dead_letter_queue_enabled": True,
                "message_retention_enabled": True,
                "message_encryption_enabled": True,
            },
        },
        "storage": {
            "encryption": {
                "at_rest": True,
                "in_transit": True,
                "algorithm": "AES-256-GCM",
            },
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "features": {
                "versioning_enabled": True,
                "backup_enabled": True,
                "replication_enabled": True,
            },
        },
        "monitoring": {
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "encryption": {
                "enabled": True,
                "alert_encryption_enabled": True,
                "log_encryption_enabled": True,
            },
        },
        "backup": {
            "encryption": {"enabled": True, "algorithm": "AES-256-GCM"},
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "features": {
                "retention_policy_enabled": True,
                "verification_enabled": True,
                "automated_backup_enabled": True,
            },
        },
        "disaster_recovery": {
            "automated_failover_enabled": True,
            "backup_replication_enabled": True,
            "recovery_testing_enabled": True,
            "documentation_enabled": True,
            "rto": "4h",  # Recovery Time Objective
            "rpo": "1h",  # Recovery Point Objective
        },
        "compliance": {
            "standards": {
                "iso27001_compliant": True,
                "soc2_compliant": True,
                "gdpr_compliant": True,
                "hipaa_compliant": True,
            },
            "audit": {
                "logging_enabled": True,
                "encryption_enabled": True,
                "retention_enabled": True,
                "alerting_enabled": True,
            },
        },
        "automation": {
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "features": {
                "approval_workflow_enabled": True,
                "rollback_enabled": True,
                "testing_enabled": True,
            },
        },
        "scaling": {
            "access_control": {"enabled": True, "audit_logging_enabled": True},
            "features": {
                "rate_limiting_enabled": True,
                "monitoring_enabled": True,
                "alerting_enabled": True,
            },
        },
        "updates": {
            "automated_updates_enabled": True,
            "rollback_enabled": True,
            "testing_enabled": True,
            "approval_required": True,
        },
        "alerting": {
            "encryption": {"enabled": True, "notification_encryption_enabled": True},
            "access_control": {"enabled": True, "audit_logging_enabled": True},
        },
    },
    # Cloud security settings
    "cloud": {
        "credentials": {
            "encryption": {"enabled": True, "algorithm": "AES-256-GCM"},
            "rotation": {"enabled": True, "interval_days": 90},
        },
        "storage": {
            "encryption": {
                "at_rest": True,
                "in_transit": True,
                "algorithm": "AES-256-GCM",
            },
            "access_control": {"enabled": True, "audit_logging_enabled": True},
        },
        "access_control": {
            "iam": {"enabled": True, "least_privilege": True, "role_based": True},
            "bucket_policies": {"enabled": True, "encryption_required": True},
        },
        "audit": {
            "logging": {
                "enabled": True,
                "encryption_enabled": True,
                "retention_days": 365,
            },
            "alerting": {"enabled": True, "notification_channels": ["email", "slack"]},
        },
    },
    # Container security settings
    "container": {
        "runtime": {
            "security_profiles": {
                "seccomp_enabled": True,
                "apparmor_enabled": True,
                "capabilities_restricted": True,
            },
            "isolation": {
                "read_only_root": True,
                "no_new_privileges": True,
                "network_isolation": True,
            },
        },
        "image": {
            "scanning": {
                "enabled": True,
                "vulnerability_threshold": "high",
                "base_image_validation": True,
            },
            "signing": {"enabled": True, "required": True},
        },
        "network": {
            "policies": {"enabled": True, "default_deny": True},
            "isolation": {"enabled": True, "dns_policy": "ClusterFirst"},
        },
        "secrets": {
            "management": {
                "enabled": True,
                "encryption_enabled": True,
                "rotation_enabled": True,
            }
        },
    },
    # Compliance security settings
    "compliance": {
        "iso27001": {
            "controls": {
                "information_security_policy": True,
                "asset_management": True,
                "access_control": True,
                "cryptography": True,
                "physical_security": True,
                "operations_security": True,
                "communications_security": True,
                "system_acquisition": True,
                "supplier_relationships": True,
                "incident_management": True,
                "business_continuity": True,
                "compliance": True,
            },
            "audit": {
                "internal_audit_enabled": True,
                "external_audit_enabled": True,
                "audit_frequency": "quarterly",
                "certification_required": True,
            },
        },
        "soc2": {
            "trust_principles": {
                "security": True,
                "availability": True,
                "processing_integrity": True,
                "confidentiality": True,
                "privacy": True,
            },
            "audit": {
                "type1_audit_enabled": True,
                "type2_audit_enabled": True,
                "audit_frequency": "annually",
                "report_distribution": ["management", "stakeholders"],
            },
        },
        "gdpr": {
            "requirements": {
                "data_protection": True,
                "data_processing": True,
                "data_subject_rights": True,
                "data_breach_notification": True,
                "data_transfer": True,
                "privacy_by_design": True,
                "data_protection_officer": True,
            },
            "documentation": {
                "privacy_policy": True,
                "data_processing_agreements": True,
                "data_protection_impact_assessments": True,
                "records_of_processing_activities": True,
            },
        },
        "hipaa": {
            "requirements": {
                "privacy_rule": True,
                "security_rule": True,
                "breach_notification": True,
                "enforcement_rule": True,
                "omnibus_rule": True,
            },
            "safeguards": {"administrative": True, "physical": True, "technical": True},
        },
        "pci_dss": {
            "requirements": {
                "network_security": True,
                "data_protection": True,
                "access_control": True,
                "monitoring": True,
                "testing": True,
                "security_policy": True,
            },
            "validation": {
                "self_assessment_enabled": True,
                "external_audit_enabled": True,
                "audit_frequency": "quarterly",
                "reporting_requirements": ["merchant", "acquirer"],
            },
        },
        "audit": {
            "logging": {
                "enabled": True,
                "encryption_enabled": True,
                "retention_enabled": True,
                "immutable_logs": True,
                "log_integrity": True,
                "retention_period": timedelta(days=365),
            },
            "reporting": {
                "automated_reporting": True,
                "report_encryption": True,
                "report_retention": True,
                "report_verification": True,
                "report_distribution": True,
                "report_frequency": "monthly",
            },
        },
        "monitoring": {
            "continuous_monitoring": True,
            "alerting_enabled": True,
            "metrics_collection": True,
            "threshold_monitoring": True,
            "compliance_dashboard": True,
            "alert_channels": ["email", "slack", "sms"],
        },
        "incident_response": {
            "detection_enabled": True,
            "response_plan": True,
            "notification_procedures": True,
            "investigation_procedures": True,
            "remediation_procedures": True,
            "response_time": "1h",
        },
        "documentation": {
            "policies_exist": True,
            "procedures_exist": True,
            "documentation_versioning": True,
            "documentation_review": True,
            "documentation_distribution": True,
            "review_frequency": "quarterly",
        },
        "training": {
            "training_program": True,
            "training_records": True,
            "training_assessment": True,
            "training_certification": True,
            "training_refresher": True,
            "training_frequency": "annually",
        },
        "risk_assessment": {
            "risk_identification": True,
            "risk_analysis": True,
            "risk_evaluation": True,
            "risk_treatment": True,
            "risk_monitoring": True,
            "assessment_frequency": "quarterly",
        },
        "vendor_management": {
            "vendor_assessment": True,
            "vendor_monitoring": True,
            "vendor_contracts": True,
            "vendor_audits": True,
            "vendor_termination": True,
            "assessment_frequency": "annually",
        },
        "change_management": {
            "change_control": True,
            "change_approval": True,
            "change_testing": True,
            "change_documentation": True,
            "change_monitoring": True,
            "approval_required": True,
        },
        "business_continuity": {
            "continuity_plan": True,
            "disaster_recovery": True,
            "backup_procedures": True,
            "recovery_testing": True,
            "emergency_procedures": True,
            "rto": "4h",
            "rpo": "1h",
        },
    },
    # Application security settings
    "application": {
        "input_validation": {
            "sql_injection": {
                "prevention_enabled": True,
                "sanitization_enabled": True,
                "parameterized_queries": True,
                "orm_usage": True,
            },
            "xss": {
                "prevention_enabled": True,
                "content_security_policy": True,
                "input_sanitization": True,
                "output_encoding": True,
            },
            "command_injection": {
                "prevention_enabled": True,
                "command_validation": True,
                "whitelist_commands": True,
                "sandbox_execution": True,
            },
            "file_upload": {
                "validation_enabled": True,
                "allowed_types": ["pdf", "doc", "docx", "txt", "jpg", "png"],
                "max_size": "10MB",
                "virus_scanning": True,
                "content_validation": True,
            },
        },
        "authentication": {
            "password_policy": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": True,
                "prevent_reuse": 5,
                "expiry_days": 90,
            },
            "brute_force": {
                "prevention_enabled": True,
                "max_attempts": 5,
                "lockout_duration": timedelta(minutes=30),
                "ip_based": True,
            },
            "session": {
                "management_enabled": True,
                "timeout": timedelta(minutes=15),
                "secure_cookies": True,
                "http_only": True,
                "same_site": "Strict",
            },
        },
        "authorization": {
            "rbac": {
                "enabled": True,
                "role_hierarchy": True,
                "permission_management": True,
                "access_control": True,
            },
            "resource_access": {
                "enforce_ownership": True,
                "allow_sharing": True,
                "sharing_permissions": ["read", "write"],
                "group_permissions": True,
            },
        },
        "api_security": {
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 100,
                "burst_limit": 50,
                "ip_based": True,
            },
            "cors": {
                "enabled": True,
                "allowed_origins": ["https://app.example.com"],
                "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
                "allowed_headers": ["Authorization", "Content-Type"],
                "max_age": 3600,
            },
            "headers": {
                "security_headers": {
                    "X-Frame-Options": "DENY",
                    "X-Content-Type-Options": "nosniff",
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "Content-Security-Policy": "default-src 'self'",
                }
            },
        },
        "data_validation": {
            "input_sanitization": {
                "enabled": True,
                "html_escaping": True,
                "sql_escaping": True,
                "command_escaping": True,
            },
            "output_encoding": {
                "enabled": True,
                "html_encoding": True,
                "url_encoding": True,
                "javascript_encoding": True,
            },
            "data_validation": {
                "enabled": True,
                "type_checking": True,
                "range_validation": True,
                "format_validation": True,
            },
        },
        "error_handling": {
            "error_messages": {
                "hide_details": True,
                "custom_messages": True,
                "logging_enabled": True,
            },
            "logging": {
                "enabled": True,
                "log_level": "ERROR",
                "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "log_rotation": True,
            },
        },
        "cryptography": {
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_rotation": True,
                "key_rotation_days": 90,
                "secure_key_storage": True,
            },
            "hashing": {
                "algorithm": "Argon2id",
                "salt_length": 32,
                "iterations": 3,
                "memory_cost": 65536,
            },
            "tls": {
                "min_version": "TLSv1.2",
                "preferred_ciphers": [
                    "ECDHE-ECDSA-AES256-GCM-SHA384",
                    "ECDHE-RSA-AES256-GCM-SHA384",
                ],
                "cert_validation": True,
            },
        },
        "secure_communication": {
            "tls": {
                "enabled": True,
                "min_version": "TLSv1.2",
                "cert_validation": True,
                "hsts_enabled": True,
            },
            "certificates": {
                "validation_enabled": True,
                "revocation_checking": True,
                "trust_store": True,
                "auto_renewal": True,
            },
        },
        "secure_storage": {
            "encryption": {
                "at_rest": True,
                "in_transit": True,
                "algorithm": "AES-256-GCM",
                "key_management": True,
            },
            "deletion": {
                "secure_deletion": True,
                "verification": True,
                "backup_removal": True,
            },
        },
        "secure_configuration": {
            "environment": {
                "production_mode": True,
                "debug_disabled": True,
                "error_reporting_disabled": True,
                "secure_headers": True,
            },
            "services": {
                "unnecessary_disabled": True,
                "default_credentials_changed": True,
                "service_isolation": True,
            },
        },
        "dependencies": {
            "security": {
                "vulnerability_scanning": True,
                "dependency_checking": True,
                "license_compliance": True,
                "update_management": True,
            },
            "updates": {
                "automatic_updates": True,
                "security_updates": True,
                "update_verification": True,
                "rollback_capability": True,
            },
        },
    },
}

# Test data configuration
TEST_DATA = {
    "users": [
        {
            "username": "test_admin",
            "password": "Test@123456",
            "role": "admin",
            "mfa_enabled": True,
        },
        {
            "username": "test_user",
            "password": "Test@123456",
            "role": "user",
            "mfa_enabled": False,
        },
    ],
    "api_keys": [
        {
            "key": "test_api_key_1",
            "permissions": ["read:own", "write:own"],
            "expires_in": timedelta(days=30),
        }
    ],
    "test_files": [
        {"name": "test_document.pdf", "type": "pdf", "size": "1MB", "encrypted": True}
    ],
}

# Test environment configuration
TEST_ENV = {
    "base_url": "http://localhost:8000",
    "test_timeout": 30,
    "logging": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    "paths": {
        "test_data": "tests/data",
        "test_output": "tests/output",
        "test_logs": "tests/logs",
    },
}

# Test utilities configuration
TEST_UTILS = {
    "password_generator": {
        "min_length": 12,
        "require_special": True,
        "require_numbers": True,
    },
    "token_generator": {"algorithm": "HS256", "expiry": timedelta(minutes=15)},
    "file_generator": {"max_size": "10MB", "allowed_types": ["pdf", "txt", "jpg"]},
    "network_generator": {"allowed_ports": [80, 443], "blocked_ports": [22, 23]},
}


def get_security_config() -> Dict[str, Any]:
    """Get security configuration."""
    return SECURITY_CONFIG


def get_test_data() -> Dict[str, Any]:
    """Get test data configuration."""
    return TEST_DATA


def get_test_env() -> Dict[str, Any]:
    """Get test environment configuration."""
    return TEST_ENV


def get_test_utils() -> Dict[str, Any]:
    """Get test utilities configuration."""
    return TEST_UTILS


def get_infrastructure_config() -> Dict[str, Any]:
    """Get infrastructure security configuration."""
    return SECURITY_CONFIG.get("infrastructure", {})


def get_cloud_config() -> Dict[str, Any]:
    """Get cloud security configuration."""
    return {
        "aws": {
            "region": os.getenv("AWS_REGION", "us-west-2"),
            "storage": {
                "encryption": {
                    "default_algorithm": "AES256",
                    "kms_key_id": os.getenv("AWS_KMS_KEY_ID", ""),
                    "enforce_encryption": True,
                },
                "bucket_policy": {
                    "enforce_secure_transport": True,
                    "block_public_access": True,
                    "require_encryption": True,
                },
                "lifecycle": {
                    "enabled": True,
                    "transition_to_ia": 30,  # days
                    "expiration": 365,  # days
                },
            },
            "secrets": {
                "rotation": {
                    "enabled": True,
                    "automatic_rotation_days": 30,
                    "require_rotation": True,
                },
                "encryption": {
                    "use_kms": True,
                    "kms_key_id": os.getenv("AWS_KMS_KEY_ID", ""),
                },
            },
            "audit": {
                "cloudtrail": {
                    "enabled": True,
                    "multi_region": True,
                    "log_validation": True,
                    "include_global_events": True,
                    "s3_bucket": os.getenv("AWS_CLOUDTRAIL_BUCKET", "test-audit-logs"),
                    "cloudwatch_logs": {
                        "enabled": True,
                        "log_group": os.getenv("AWS_CLOUDWATCH_LOG_GROUP", "test-logs"),
                        "role_arn": os.getenv("AWS_CLOUDWATCH_ROLE_ARN", ""),
                    },
                }
            },
        },
        "gcp": {
            "project_id": os.getenv("GCP_PROJECT_ID", "test-project"),
            "storage": {
                "encryption": {
                    "default_kms_key": os.getenv("GCP_KMS_KEY", ""),
                    "enforce_encryption": True,
                },
                "bucket_iam": {
                    "uniform_bucket_level_access": True,
                    "public_access_prevention": "enforced",
                    "require_secure_transport": True,
                },
                "lifecycle": {
                    "enabled": True,
                    "transition_to_coldline": 30,  # days
                    "delete_after": 365,  # days
                },
            },
            "secrets": {
                "rotation": {
                    "enabled": True,
                    "rotation_period_seconds": 2592000,  # 30 days
                    "require_rotation": True,
                },
                "encryption": {
                    "use_kms": True,
                    "kms_key": os.getenv("GCP_KMS_KEY", ""),
                },
            },
            "audit": {
                "logging": {
                    "enabled": True,
                    "log_bucket": os.getenv("GCP_LOG_BUCKET", "test-audit-logs"),
                    "log_sink": {
                        "enabled": True,
                        "destination": os.getenv("GCP_LOG_SINK_DESTINATION", ""),
                        "filter": "resource.type=gcs_bucket",
                        "include_children": True,
                    },
                }
            },
        },
    }


def get_container_config() -> Dict[str, Any]:
    """Get container security configuration."""
    return {
        "runtime": {
            "security": {
                "seccomp": {"enabled": True, "profile": "unconfined"},
                "apparmor": {"enabled": True, "profile": "unconfined"},
                "capabilities": {"drop_all": True, "allowed": ["NET_BIND_SERVICE"]},
                "read_only_root": True,
                "no_new_privileges": True,
            },
            "resources": {
                "memory_limit": "512m",
                "cpu_period": 100000,
                "cpu_quota": 50000,
                "pids_limit": 100,
            },
        },
        "image": {
            "scanning": {
                "enabled": True,
                "vulnerability_threshold": "high",
                "require_scan": True,
            },
            "signing": {
                "enabled": True,
                "require_signature": True,
                "key_id": os.getenv("CONTAINER_SIGNING_KEY", ""),
            },
        },
        "kubernetes": {
            "pod_security": {
                "run_as_non_root": True,
                "run_as_user": 1000,
                "run_as_group": 3000,
                "fs_group": 2000,
                "allow_privilege_escalation": False,
                "read_only_root_filesystem": True,
            },
            "network": {
                "policies_enabled": True,
                "default_deny": True,
                "isolation_enabled": True,
            },
        },
        "secrets": {
            "management": {
                "enabled": True,
                "encryption_enabled": True,
                "rotation_enabled": True,
                "rotation_period_days": 30,
            }
        },
    }


def get_compliance_config() -> Dict[str, Any]:
    """Get compliance security configuration."""
    return SECURITY_CONFIG.get("compliance", {})


def get_application_config() -> Dict[str, Any]:
    """Get application security configuration."""
    return {
        "authentication": {
            "enabled": True,
            "require_mfa": True,
            "session_timeout_minutes": 30,
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 15,
        },
        "authorization": {
            "enabled": True,
            "rbac_enabled": True,
            "require_least_privilege": True,
            "audit_enabled": True,
        },
        "api_security": {
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 100,
                "burst_limit": 50,
            },
            "input_validation": {
                "enabled": True,
                "sanitize_inputs": True,
                "validate_content_types": True,
            },
            "cors": {
                "enabled": True,
                "allowed_origins": ["https://example.com"],
                "allowed_methods": ["GET", "POST"],
                "allowed_headers": ["Content-Type", "Authorization"],
            },
        },
        "data_security": {
            "encryption": {
                "at_rest": {"enabled": True, "algorithm": "AES-256-GCM"},
                "in_transit": {
                    "enabled": True,
                    "require_tls": True,
                    "min_tls_version": "TLSv1.2",
                },
            },
            "validation": {
                "enabled": True,
                "sanitize_outputs": True,
                "validate_schemas": True,
            },
        },
        "logging": {
            "enabled": True,
            "level": "INFO",
            "retention_days": 90,
            "audit_logging": {"enabled": True, "include_sensitive_data": False},
        },
        "monitoring": {
            "enabled": True,
            "alerting": {
                "enabled": True,
                "notification_channels": ["email", "slack"],
                "critical_threshold": 0.95,
            },
            "metrics": {
                "enabled": True,
                "collection_interval_seconds": 60,
                "retention_days": 30,
            },
        },
    }
