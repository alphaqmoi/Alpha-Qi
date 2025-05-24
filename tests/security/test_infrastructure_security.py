"""Infrastructure security tests."""

import pytest
import json
import requests
import socket
import ssl
import subprocess
from typing import Dict, Any
from datetime import datetime, timedelta
import docker
import kubernetes
import terraform
import ansible
import nmap
import paramiko

from services.security import SecurityService, SecurityException
from services.monitoring import MonitoringService
from services.audit import AuditService
from tests.security.config import get_security_config

@pytest.mark.security
class TestInfrastructureSecurity:
    """Test infrastructure security features."""

    def test_network_segmentation(self, security_test_client, security_config):
        """Test network segmentation and isolation."""
        client, _ = security_test_client()
        
        # Test network isolation between environments
        response = client.get("/api/infrastructure/network/segmentation")
        segments = response.json['segments']
        
        # Verify production and staging networks are isolated
        assert segments['production']['isolated']
        assert segments['staging']['isolated']
        assert not segments['production']['can_access_staging']
        assert not segments['staging']['can_access_production']

    def test_load_balancer_security(self, security_test_client, security_config):
        """Test load balancer security configuration."""
        client, _ = security_test_client()
        
        # Test load balancer health checks
        response = client.get("/api/infrastructure/loadbalancer/health")
        health = response.json['health']
        
        # Verify SSL termination and health check configuration
        assert health['ssl_termination_enabled']
        assert health['health_check_enabled']
        assert health['ddos_protection_enabled']
        assert health['waf_enabled']

    def test_database_security(self, security_test_client, security_config):
        """Test database security measures."""
        client, _ = security_test_client()
        
        # Test database encryption
        response = client.get("/api/infrastructure/database/security")
        db_security = response.json['security']
        
        # Verify encryption and access controls
        assert db_security['encryption_at_rest']
        assert db_security['encryption_in_transit']
        assert db_security['access_control_enabled']
        assert db_security['audit_logging_enabled']

    def test_caching_security(self, security_test_client, security_config):
        """Test caching infrastructure security."""
        client, _ = security_test_client()
        
        # Test cache security
        response = client.get("/api/infrastructure/cache/security")
        cache_security = response.json['security']
        
        # Verify cache isolation and encryption
        assert cache_security['encryption_enabled']
        assert cache_security['isolation_enabled']
        assert cache_security['access_control_enabled']
        assert not cache_security['allow_public_access']

    def test_queue_security(self, security_test_client, security_config):
        """Test message queue security."""
        client, _ = security_test_client()
        
        # Test queue security
        response = client.get("/api/infrastructure/queue/security")
        queue_security = response.json['security']
        
        # Verify queue encryption and access controls
        assert queue_security['encryption_enabled']
        assert queue_security['access_control_enabled']
        assert queue_security['dead_letter_queue_enabled']
        assert queue_security['message_retention_enabled']

    def test_storage_security(self, security_test_client, security_config):
        """Test storage infrastructure security."""
        client, _ = security_test_client()
        
        # Test storage security
        response = client.get("/api/infrastructure/storage/security")
        storage_security = response.json['security']
        
        # Verify storage encryption and access controls
        assert storage_security['encryption_at_rest']
        assert storage_security['encryption_in_transit']
        assert storage_security['access_control_enabled']
        assert storage_security['versioning_enabled']

    def test_monitoring_security(self, security_test_client, security_config):
        """Test monitoring infrastructure security."""
        client, _ = security_test_client()
        
        # Test monitoring security
        response = client.get("/api/infrastructure/monitoring/security")
        monitoring_security = response.json['security']
        
        # Verify monitoring access controls and encryption
        assert monitoring_security['access_control_enabled']
        assert monitoring_security['encryption_enabled']
        assert monitoring_security['alert_encryption_enabled']
        assert monitoring_security['log_encryption_enabled']

    def test_backup_security(self, security_test_client, security_config):
        """Test backup infrastructure security."""
        client, _ = security_test_client()
        
        # Test backup security
        response = client.get("/api/infrastructure/backup/security")
        backup_security = response.json['security']
        
        # Verify backup encryption and access controls
        assert backup_security['encryption_enabled']
        assert backup_security['access_control_enabled']
        assert backup_security['retention_policy_enabled']
        assert backup_security['verification_enabled']

    def test_disaster_recovery(self, security_test_client, security_config):
        """Test disaster recovery infrastructure."""
        client, _ = security_test_client()
        
        # Test DR configuration
        response = client.get("/api/infrastructure/disaster-recovery/config")
        dr_config = response.json['config']
        
        # Verify DR settings
        assert dr_config['automated_failover_enabled']
        assert dr_config['backup_replication_enabled']
        assert dr_config['recovery_testing_enabled']
        assert dr_config['documentation_enabled']

    def test_infrastructure_compliance(self, security_test_client, security_config):
        """Test infrastructure compliance controls."""
        client, _ = security_test_client()
        
        # Test compliance status
        response = client.get("/api/infrastructure/compliance/status")
        compliance = response.json['compliance']
        
        # Verify compliance controls
        assert compliance['iso27001_compliant']
        assert compliance['soc2_compliant']
        assert compliance['gdpr_compliant']
        assert compliance['hipaa_compliant']

    def test_infrastructure_audit(self, security_test_client, security_config):
        """Test infrastructure audit logging."""
        client, _ = security_test_client()
        
        # Test audit logging
        response = client.get("/api/infrastructure/audit/logs")
        audit_logs = response.json['logs']
        
        # Verify audit logging configuration
        assert audit_logs['logging_enabled']
        assert audit_logs['encryption_enabled']
        assert audit_logs['retention_enabled']
        assert audit_logs['alerting_enabled']

    def test_infrastructure_automation(self, security_test_client, security_config):
        """Test infrastructure automation security."""
        client, _ = security_test_client()
        
        # Test automation security
        response = client.get("/api/infrastructure/automation/security")
        automation_security = response.json['security']
        
        # Verify automation security controls
        assert automation_security['access_control_enabled']
        assert automation_security['audit_logging_enabled']
        assert automation_security['approval_workflow_enabled']
        assert automation_security['rollback_enabled']

    def test_infrastructure_scaling(self, security_test_client, security_config):
        """Test infrastructure scaling security."""
        client, _ = security_test_client()
        
        # Test scaling security
        response = client.get("/api/infrastructure/scaling/security")
        scaling_security = response.json['security']
        
        # Verify scaling security controls
        assert scaling_security['access_control_enabled']
        assert scaling_security['rate_limiting_enabled']
        assert scaling_security['monitoring_enabled']
        assert scaling_security['alerting_enabled']

    def test_infrastructure_updates(self, security_test_client, security_config):
        """Test infrastructure update security."""
        client, _ = security_test_client()
        
        # Test update security
        response = client.get("/api/infrastructure/updates/security")
        update_security = response.json['security']
        
        # Verify update security controls
        assert update_security['automated_updates_enabled']
        assert update_security['rollback_enabled']
        assert update_security['testing_enabled']
        assert update_security['approval_required']

    def test_infrastructure_monitoring(self, security_test_client, security_config):
        """Test infrastructure monitoring security."""
        client, _ = security_test_client()
        
        # Test monitoring security
        response = client.get("/api/infrastructure/monitoring/security")
        monitoring_security = response.json['security']
        
        # Verify monitoring security controls
        assert monitoring_security['access_control_enabled']
        assert monitoring_security['encryption_enabled']
        assert monitoring_security['alerting_enabled']
        assert monitoring_security['logging_enabled']

    def test_infrastructure_alerting(self, security_test_client, security_config):
        """Test infrastructure alerting security."""
        client, _ = security_test_client()
        
        # Test alerting security
        response = client.get("/api/infrastructure/alerting/security")
        alerting_security = response.json['security']
        
        # Verify alerting security controls
        assert alerting_security['encryption_enabled']
        assert alerting_security['access_control_enabled']
        assert alerting_security['audit_logging_enabled']
        assert alerting_security['notification_encryption_enabled']

@pytest.mark.security
@pytest.mark.infrastructure
class TestContainerSecurity:
    """Test container infrastructure security features."""

    def test_docker_security(self, security_test_client, security_config):
        """Test Docker security features.
        
        This test verifies:
        - Container isolation
        - Resource limits
        - Security profiles
        - Image scanning
        """
        client = docker.from_env()
        security_service = SecurityService()
        
        # Test container isolation
        container_config = {
            'image': 'nginx:latest',
            'detach': True,
            'security_opt': [
                'no-new-privileges',
                'seccomp=unconfined'
            ],
            'cap_drop': ['ALL'],
            'cap_add': ['NET_BIND_SERVICE'],
            'ulimits': [
                docker.types.Ulimit(name='nofile', soft=1024, hard=2048)
            ]
        }
        
        try:
            container = client.containers.run(**container_config)
            
            # Verify security settings
            inspect = client.api.inspect_container(container.id)
            assert 'no-new-privileges' in inspect['HostConfig']['SecurityOpt']
            assert 'ALL' in inspect['HostConfig']['CapDrop']
            
            # Test resource limits
            container.update(
                cpu_quota=50000,  # 50% of CPU
                mem_limit='512m',
                memswap_limit='1g'
            )
            
            limits = client.api.inspect_container(container.id)['HostConfig']
            assert limits['CpuQuota'] == 50000
            assert limits['Memory'] == 536870912  # 512MB in bytes
            
        finally:
            container.remove(force=True)

    def test_kubernetes_security(self, security_test_client, security_config):
        """Test Kubernetes security features.
        
        This test verifies:
        - Pod security policies
        - Network policies
        - RBAC
        - Secrets management
        """
        k8s_client = kubernetes.client.CoreV1Api()
        security_service = SecurityService()
        
        # Test pod security
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': 'test-secure-pod',
                'namespace': 'default'
            },
            'spec': {
                'containers': [{
                    'name': 'nginx',
                    'image': 'nginx:latest',
                    'securityContext': {
                        'runAsNonRoot': True,
                        'runAsUser': 1000,
                        'allowPrivilegeEscalation': False,
                        'capabilities': {
                            'drop': ['ALL']
                        }
                    }
                }]
            }
        }
        
        try:
            # Create pod
            pod = k8s_client.create_namespaced_pod(
                namespace='default',
                body=pod_manifest
            )
            
            # Verify security settings
            pod_info = k8s_client.read_namespaced_pod(
                name='test-secure-pod',
                namespace='default'
            )
            
            security_context = pod_info.spec.containers[0].security_context
            assert security_context.run_as_non_root
            assert security_context.run_as_user == 1000
            assert not security_context.allow_privilege_escalation
            
        finally:
            k8s_client.delete_namespaced_pod(
                name='test-secure-pod',
                namespace='default'
            )

@pytest.mark.security
@pytest.mark.infrastructure
class TestNetworkSecurity:
    """Test network infrastructure security features."""

    def test_firewall_security(self, security_test_client, security_config):
        """Test firewall security features.
        
        This test verifies:
        - Firewall rules
        - Port scanning
        - Access control
        - Traffic monitoring
        """
        nm = nmap.PortScanner()
        security_service = SecurityService()
        
        # Test port scanning
        target_host = 'localhost'
        nm.scan(target_host, '20-25,80,443,3306,5432')
        
        # Verify only expected ports are open
        open_ports = []
        for host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                ports = nm[host][proto].keys()
                open_ports.extend(ports)
        
        # Only allow specific ports
        allowed_ports = {80, 443}  # HTTP and HTTPS
        assert all(port in allowed_ports for port in open_ports)
        
        # Test firewall rules
        firewall_rules = security_service.get_firewall_rules()
        assert any(rule['port'] == 80 and rule['action'] == 'allow' 
                  for rule in firewall_rules)
        assert any(rule['port'] == 3306 and rule['action'] == 'deny' 
                  for rule in firewall_rules)

    def test_ssl_security(self, security_test_client, security_config):
        """Test SSL/TLS security features.
        
        This test verifies:
        - Certificate validation
        - Protocol versions
        - Cipher suites
        - Certificate expiration
        """
        security_service = SecurityService()
        
        # Test SSL connection
        hostname = 'example.com'
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                # Verify certificate
                assert cert is not None
                assert ssl.match_hostname(cert, hostname)
                
                # Check protocol version
                assert ssock.version() in ['TLSv1.2', 'TLSv1.3']
                
                # Verify cipher suite
                cipher = ssock.cipher()
                assert cipher[0] in security_service.get_allowed_ciphers()
                
                # Check certificate expiration
                not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                assert not_after > datetime.now()

@pytest.mark.security
@pytest.mark.infrastructure
class TestInfrastructureCompliance:
    """Test infrastructure compliance features."""

    def test_terraform_security(self, security_test_client, security_config):
        """Test Terraform security features.
        
        This test verifies:
        - State file encryption
        - Access control
        - Resource tagging
        - Compliance policies
        """
        terraform_client = terraform.Terraform()
        security_service = SecurityService()
        
        # Test state file security
        state_config = {
            'backend': {
                's3': {
                    'bucket': 'terraform-state',
                    'key': 'test/terraform.tfstate',
                    'region': 'us-west-2',
                    'encrypt': True,
                    'kms_key_id': 'arn:aws:kms:region:account:key/key-id'
                }
            }
        }
        
        # Verify state encryption
        assert state_config['backend']['s3']['encrypt']
        assert 'kms_key_id' in state_config['backend']['s3']
        
        # Test resource tagging
        resource_config = {
            'resource': {
                'aws_instance': {
                    'test': {
                        'tags': {
                            'Environment': 'test',
                            'SecurityLevel': 'high',
                            'Compliance': 'HIPAA'
                        }
                    }
                }
            }
        }
        
        # Verify required tags
        required_tags = {'Environment', 'SecurityLevel', 'Compliance'}
        assert all(tag in resource_config['resource']['aws_instance']['test']['tags'] 
                  for tag in required_tags)

    def test_ansible_security(self, security_test_client, security_config):
        """Test Ansible security features.
        
        This test verifies:
        - Playbook encryption
        - Vault usage
        - Role security
        - Task validation
        """
        ansible_client = ansible.Ansible()
        security_service = SecurityService()
        
        # Test playbook security
        playbook = {
            'name': 'Secure server configuration',
            'hosts': 'all',
            'become': True,
            'vars_files': ['vault.yml'],
            'tasks': [
                {
                    'name': 'Configure SSH',
                    'template': {
                        'src': 'sshd_config.j2',
                        'dest': '/etc/ssh/sshd_config',
                        'mode': '0600',
                        'owner': 'root',
                        'group': 'root'
                    }
                },
                {
                    'name': 'Enable firewall',
                    'service': {
                        'name': 'ufw',
                        'state': 'started',
                        'enabled': True
                    }
                }
            ]
        }
        
        # Verify playbook security
        assert playbook['vars_files'] == ['vault.yml']  # Using Ansible Vault
        assert playbook['become']  # Using privilege escalation
        
        # Test task security
        for task in playbook['tasks']:
            if 'template' in task:
                assert task['template']['mode'] == '0600'
                assert task['template']['owner'] == 'root'
                assert task['template']['group'] == 'root'

@pytest.mark.security
@pytest.mark.infrastructure
class TestMonitoringSecurity:
    """Test infrastructure monitoring security features."""

    def test_logging_security(self, security_test_client, security_config):
        """Test logging security features.
        
        This test verifies:
        - Log encryption
        - Access control
        - Retention policies
        - Audit logging
        """
        security_service = SecurityService()
        
        # Test log encryption
        log_config = {
            'encryption': {
                'enabled': True,
                'algorithm': 'AES-256-GCM',
                'key_rotation': '30d'
            },
            'retention': {
                'period': '90d',
                'archive': True
            },
            'access_control': {
                'require_auth': True,
                'audit_logging': True
            }
        }
        
        # Verify log security
        assert log_config['encryption']['enabled']
        assert log_config['encryption']['algorithm'] == 'AES-256-GCM'
        assert log_config['access_control']['require_auth']
        assert log_config['access_control']['audit_logging']

    def test_alerting_security(self, security_test_client, security_config):
        """Test alerting security features.
        
        This test verifies:
        - Alert encryption
        - Notification security
        - Alert validation
        - Response automation
        """
        security_service = SecurityService()
        
        # Test alert configuration
        alert_config = {
            'encryption': {
                'enabled': True,
                'method': 'end-to-end'
            },
            'notifications': {
                'channels': ['email', 'slack'],
                'require_ack': True,
                'timeout': '15m'
            },
            'validation': {
                'rate_limiting': True,
                'duplicate_detection': True
            },
            'automation': {
                'enabled': True,
                'actions': ['block_ip', 'disable_account']
            }
        }
        
        # Verify alert security
        assert alert_config['encryption']['enabled']
        assert alert_config['encryption']['method'] == 'end-to-end'
        assert alert_config['notifications']['require_ack']
        assert alert_config['validation']['rate_limiting']
        assert alert_config['automation']['enabled'] 