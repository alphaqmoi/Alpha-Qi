"""Compliance security tests."""

import pytest
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any

from services.security import SecurityService, SecurityException
from services.compliance import ComplianceService
from services.audit import AuditService

@pytest.mark.security
class TestComplianceSecurity:
    """Test compliance security features."""

    def test_iso27001_compliance(self, security_test_client, security_config):
        """Test ISO27001 compliance controls."""
        client, _ = security_test_client()
        
        # Test ISO27001 controls
        response = client.get("/api/compliance/iso27001/status")
        compliance = response.json['compliance']
        
        # Verify key ISO27001 controls
        assert compliance['information_security_policy']
        assert compliance['asset_management']
        assert compliance['access_control']
        assert compliance['cryptography']
        assert compliance['physical_security']
        assert compliance['operations_security']
        assert compliance['communications_security']
        assert compliance['system_acquisition']
        assert compliance['supplier_relationships']
        assert compliance['incident_management']
        assert compliance['business_continuity']
        assert compliance['compliance']

    def test_soc2_compliance(self, security_test_client, security_config):
        """Test SOC2 compliance controls."""
        client, _ = security_test_client()
        
        # Test SOC2 controls
        response = client.get("/api/compliance/soc2/status")
        compliance = response.json['compliance']
        
        # Verify SOC2 trust principles
        assert compliance['security']
        assert compliance['availability']
        assert compliance['processing_integrity']
        assert compliance['confidentiality']
        assert compliance['privacy']

    def test_gdpr_compliance(self, security_test_client, security_config):
        """Test GDPR compliance controls."""
        client, _ = security_test_client()
        
        # Test GDPR controls
        response = client.get("/api/compliance/gdpr/status")
        compliance = response.json['compliance']
        
        # Verify GDPR requirements
        assert compliance['data_protection']
        assert compliance['data_processing']
        assert compliance['data_subject_rights']
        assert compliance['data_breach_notification']
        assert compliance['data_transfer']
        assert compliance['privacy_by_design']
        assert compliance['data_protection_officer']

    def test_hipaa_compliance(self, security_test_client, security_config):
        """Test HIPAA compliance controls."""
        client, _ = security_test_client()
        
        # Test HIPAA controls
        response = client.get("/api/compliance/hipaa/status")
        compliance = response.json['compliance']
        
        # Verify HIPAA requirements
        assert compliance['privacy_rule']
        assert compliance['security_rule']
        assert compliance['breach_notification']
        assert compliance['enforcement_rule']
        assert compliance['omnibus_rule']

    def test_pci_dss_compliance(self, security_test_client, security_config):
        """Test PCI DSS compliance controls."""
        client, _ = security_test_client()
        
        # Test PCI DSS controls
        response = client.get("/api/compliance/pci/status")
        compliance = response.json['compliance']
        
        # Verify PCI DSS requirements
        assert compliance['network_security']
        assert compliance['data_protection']
        assert compliance['access_control']
        assert compliance['monitoring']
        assert compliance['testing']
        assert compliance['security_policy']

    def test_compliance_audit_logging(self, security_test_client, security_config):
        """Test compliance audit logging."""
        client, _ = security_test_client()
        
        # Test audit logging
        response = client.get("/api/compliance/audit/logs")
        audit_logs = response.json['logs']
        
        # Verify audit logging requirements
        assert audit_logs['logging_enabled']
        assert audit_logs['encryption_enabled']
        assert audit_logs['retention_enabled']
        assert audit_logs['immutable_logs']
        assert audit_logs['log_integrity']

    def test_compliance_reporting(self, security_test_client, security_config):
        """Test compliance reporting."""
        client, _ = security_test_client()
        
        # Test compliance reports
        response = client.get("/api/compliance/reports")
        reports = response.json['reports']
        
        # Verify reporting capabilities
        assert reports['automated_reporting']
        assert reports['report_encryption']
        assert reports['report_retention']
        assert reports['report_verification']
        assert reports['report_distribution']

    def test_compliance_monitoring(self, security_test_client, security_config):
        """Test compliance monitoring."""
        client, _ = security_test_client()
        
        # Test compliance monitoring
        response = client.get("/api/compliance/monitoring/status")
        monitoring = response.json['monitoring']
        
        # Verify monitoring capabilities
        assert monitoring['continuous_monitoring']
        assert monitoring['alerting_enabled']
        assert monitoring['metrics_collection']
        assert monitoring['threshold_monitoring']
        assert monitoring['compliance_dashboard']

    def test_compliance_incident_response(self, security_test_client, security_config):
        """Test compliance incident response."""
        client, _ = security_test_client()
        
        # Test incident response
        response = client.get("/api/compliance/incident/response")
        incident_response = response.json['response']
        
        # Verify incident response capabilities
        assert incident_response['detection_enabled']
        assert incident_response['response_plan']
        assert incident_response['notification_procedures']
        assert incident_response['investigation_procedures']
        assert incident_response['remediation_procedures']

    def test_compliance_documentation(self, security_test_client, security_config):
        """Test compliance documentation."""
        client, _ = security_test_client()
        
        # Test documentation
        response = client.get("/api/compliance/documentation")
        documentation = response.json['documentation']
        
        # Verify documentation requirements
        assert documentation['policies_exist']
        assert documentation['procedures_exist']
        assert documentation['documentation_versioning']
        assert documentation['documentation_review']
        assert documentation['documentation_distribution']

    def test_compliance_training(self, security_test_client, security_config):
        """Test compliance training."""
        client, _ = security_test_client()
        
        # Test training
        response = client.get("/api/compliance/training/status")
        training = response.json['training']
        
        # Verify training requirements
        assert training['training_program']
        assert training['training_records']
        assert training['training_assessment']
        assert training['training_certification']
        assert training['training_refresher']

    def test_compliance_risk_assessment(self, security_test_client, security_config):
        """Test compliance risk assessment."""
        client, _ = security_test_client()
        
        # Test risk assessment
        response = client.get("/api/compliance/risk/assessment")
        risk_assessment = response.json['assessment']
        
        # Verify risk assessment requirements
        assert risk_assessment['risk_identification']
        assert risk_assessment['risk_analysis']
        assert risk_assessment['risk_evaluation']
        assert risk_assessment['risk_treatment']
        assert risk_assessment['risk_monitoring']

    def test_compliance_vendor_management(self, security_test_client, security_config):
        """Test compliance vendor management."""
        client, _ = security_test_client()
        
        # Test vendor management
        response = client.get("/api/compliance/vendor/management")
        vendor_management = response.json['management']
        
        # Verify vendor management requirements
        assert vendor_management['vendor_assessment']
        assert vendor_management['vendor_monitoring']
        assert vendor_management['vendor_contracts']
        assert vendor_management['vendor_audits']
        assert vendor_management['vendor_termination']

    def test_compliance_change_management(self, security_test_client, security_config):
        """Test compliance change management."""
        client, _ = security_test_client()
        
        # Test change management
        response = client.get("/api/compliance/change/management")
        change_management = response.json['management']
        
        # Verify change management requirements
        assert change_management['change_control']
        assert change_management['change_approval']
        assert change_management['change_testing']
        assert change_management['change_documentation']
        assert change_management['change_monitoring']

    def test_compliance_business_continuity(self, security_test_client, security_config):
        """Test compliance business continuity."""
        client, _ = security_test_client()
        
        # Test business continuity
        response = client.get("/api/compliance/business/continuity")
        business_continuity = response.json['continuity']
        
        # Verify business continuity requirements
        assert business_continuity['continuity_plan']
        assert business_continuity['disaster_recovery']
        assert business_continuity['backup_procedures']
        assert business_continuity['recovery_testing']
        assert business_continuity['emergency_procedures'] 