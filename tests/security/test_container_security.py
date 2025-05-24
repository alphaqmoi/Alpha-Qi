"""Container security tests."""

import pytest
import docker
from kubernetes import client, config
from typing import Dict, Any
import json
import os
from datetime import datetime, timedelta

from services.security import SecurityService
from services.container import ContainerService
from tests.security.config import get_container_config

@pytest.fixture
def docker_client():
    """Create Docker client fixture."""
    return docker.from_env()

@pytest.fixture
def k8s_client():
    """Create Kubernetes client fixture."""
    config.load_kube_config()
    return client.CoreV1Api()

@pytest.mark.security
@pytest.mark.container
class TestContainerRuntimeSecurity:
    """Test container runtime security features."""

    def test_container_runtime_configuration(self, docker_client, security_test_client, security_config):
        """Test container runtime security configuration."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test container security profile
        container = docker_client.containers.run(
            'alpine:latest',
            'sleep 3600',
            detach=True,
            security_opt=[
                'seccomp=unconfined',
                'apparmor=unconfined',
                'no-new-privileges'
            ],
            cap_drop=['ALL'],
            cap_add=['NET_BIND_SERVICE'],
            read_only=True
        )
        
        try:
            # Verify container security settings
            container_info = docker_client.api.inspect_container(container.id)
            assert container_info['HostConfig']['SecurityOpt'] == ['seccomp=unconfined', 'apparmor=unconfined', 'no-new-privileges']
            assert container_info['HostConfig']['ReadonlyRootfs'] is True
            assert 'ALL' in container_info['HostConfig']['CapDrop']
            assert 'NET_BIND_SERVICE' in container_info['HostConfig']['CapAdd']
        finally:
            container.stop()
            container.remove()

    def test_container_resource_limits(self, docker_client, security_test_client, security_config):
        """Test container resource limits."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test container with resource limits
        container = docker_client.containers.run(
            'alpine:latest',
            'sleep 3600',
            detach=True,
            mem_limit='512m',
            cpu_period=100000,
            cpu_quota=50000,
            pids_limit=100
        )
        
        try:
            # Verify resource limits
            container_info = docker_client.api.inspect_container(container.id)
            assert container_info['HostConfig']['Memory'] == 536870912  # 512MB in bytes
            assert container_info['HostConfig']['CpuPeriod'] == 100000
            assert container_info['HostConfig']['CpuQuota'] == 50000
            assert container_info['HostConfig']['PidsLimit'] == 100
        finally:
            container.stop()
            container.remove()

    def test_container_network_isolation(self, docker_client, security_test_client, security_config):
        """Test container network isolation settings."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test container with network isolation
        container = docker_client.containers.run(
            'alpine:latest',
            'sleep 3600',
            detach=True,
            network_mode='none',  # Isolated network
            dns=['8.8.8.8'],  # Custom DNS
            dns_opt=['ndots:1'],
            dns_search=['example.com']
        )
        
        try:
            # Verify network isolation
            container_info = docker_client.api.inspect_container(container.id)
            assert container_info['HostConfig']['NetworkMode'] == 'none'
            assert container_info['HostConfig']['Dns'] == ['8.8.8.8']
            assert container_info['HostConfig']['DnsOptions'] == ['ndots:1']
            assert container_info['HostConfig']['DnsSearch'] == ['example.com']
        finally:
            container.stop()
            container.remove()

    def test_container_security_scanning(self, docker_client, security_test_client, security_config):
        """Test container security scanning."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test container with security scanning
        test_image = docker_client.images.build(
            path='tests/fixtures/test-image',
            tag='test-security-scan:latest',
            rm=True,
            buildargs={
                'SCAN_LEVEL': 'high',
                'SCAN_TIMEOUT': '300'
            }
        )
        
        try:
            # Run security scan
            scan_result = docker_client.images.scan(
                test_image.id,
                scan_type='vulnerability',
                scan_level='high'
            )
            
            # Verify scan results
            assert scan_result['scan_status'] == 'completed'
            assert 'vulnerabilities' in scan_result
            assert 'critical' not in scan_result['vulnerabilities']
            assert 'high' not in scan_result['vulnerabilities']
            
            # Test runtime scanning
            container = docker_client.containers.run(
                test_image.id,
                'sleep 3600',
                detach=True,
                security_opt=['no-new-privileges'],
                cap_drop=['ALL'],
                read_only=True
            )
            
            runtime_scan = docker_client.api.inspect_container(container.id)
            assert runtime_scan['HostConfig']['SecurityOpt'] == ['no-new-privileges']
            assert runtime_scan['HostConfig']['ReadonlyRootfs'] is True
            assert 'ALL' in runtime_scan['HostConfig']['CapDrop']
        finally:
            docker_client.images.remove(test_image.id)

    def test_container_resource_isolation(self, docker_client, security_test_client, security_config):
        """Test container resource isolation."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test container with resource isolation
        container = docker_client.containers.run(
            'alpine:latest',
            'sleep 3600',
            detach=True,
            mem_limit='512m',
            memswap_limit='1g',
            cpu_shares=512,
            cpu_period=100000,
            cpu_quota=50000,
            pids_limit=100,
            ulimits=[
                docker.types.Ulimit(name='nofile', soft=1024, hard=2048),
                docker.types.Ulimit(name='nproc', soft=1024, hard=2048)
            ]
        )
        
        try:
            # Verify resource isolation
            container_info = docker_client.api.inspect_container(container.id)
            assert container_info['HostConfig']['Memory'] == 536870912  # 512MB
            assert container_info['HostConfig']['MemorySwap'] == 1073741824  # 1GB
            assert container_info['HostConfig']['CpuShares'] == 512
            assert container_info['HostConfig']['CpuPeriod'] == 100000
            assert container_info['HostConfig']['CpuQuota'] == 50000
            assert container_info['HostConfig']['PidsLimit'] == 100
            
            # Verify ulimits
            ulimits = container_info['HostConfig']['Ulimits']
            assert any(ulimit['Name'] == 'nofile' and ulimit['Soft'] == 1024 for ulimit in ulimits)
            assert any(ulimit['Name'] == 'nproc' and ulimit['Soft'] == 1024 for ulimit in ulimits)
        finally:
            container.stop()
            container.remove()

@pytest.mark.security
@pytest.mark.container
class TestContainerImageSecurity:
    """Test container image security features."""

    def test_image_vulnerability_scanning(self, docker_client, security_test_client, security_config):
        """Test container image vulnerability scanning."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Build test image
        test_image = docker_client.images.build(
            path='tests/fixtures/test-image',
            tag='test-image:latest',
            rm=True
        )
        
        try:
            # Scan image for vulnerabilities
            scan_result = docker_client.images.scan(test_image.id)
            
            # Verify scan results
            assert scan_result['vulnerabilities'] is not None
            assert scan_result['scan_status'] == 'completed'
            assert len(scan_result['vulnerabilities']) == 0  # No vulnerabilities in test image
        finally:
            docker_client.images.remove(test_image.id)

    def test_image_signing_verification(self, docker_client, security_test_client, security_config):
        """Test container image signing and verification."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test image signing
        response = client.post("/api/container/image/sign", json={
            "image": "test-image:latest",
            "signing_key": "test-key"
        })
        
        assert response.status_code == 200
        assert response.json['signed'] is True
        
        # Test image verification
        verify_response = client.post("/api/container/image/verify", json={
            "image": "test-image:latest"
        })
        
        assert verify_response.status_code == 200
        assert verify_response.json['verified'] is True

    def test_image_base_security(self, docker_client, security_test_client, security_config):
        """Test container base image security."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test base image security
        test_image = docker_client.images.build(
            path='tests/fixtures/test-image',
            tag='test-base-security:latest',
            rm=True,
            buildargs={
                'BASE_IMAGE': 'alpine:3.14',
                'SECURITY_SCAN': 'true'
            }
        )
        
        try:
            # Verify base image
            image_info = docker_client.api.inspect_image(test_image.id)
            assert 'alpine:3.14' in image_info['RepoTags'][0]
            
            # Test image layers
            history = docker_client.api.history(test_image.id)
            assert len(history) > 0
            
            # Verify no sensitive data in layers
            for layer in history:
                assert 'password' not in layer.get('CreatedBy', '').lower()
                assert 'secret' not in layer.get('CreatedBy', '').lower()
                assert 'key' not in layer.get('CreatedBy', '').lower()
            
            # Test image signing
            sign_result = docker_client.images.sign(
                test_image.id,
                key_id=container_config['image']['signing']['key_id']
            )
            assert sign_result['signed'] is True
        finally:
            docker_client.images.remove(test_image.id)

    def test_image_dependency_security(self, docker_client, security_test_client, security_config):
        """Test container image dependency security."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test dependency security
        test_image = docker_client.images.build(
            path='tests/fixtures/test-image',
            tag='test-dependency-security:latest',
            rm=True,
            buildargs={
                'SCAN_DEPENDENCIES': 'true',
                'UPDATE_DEPENDENCIES': 'true'
            }
        )
        
        try:
            # Scan dependencies
            scan_result = docker_client.images.scan(
                test_image.id,
                scan_type='dependency',
                scan_level='high'
            )
            
            # Verify dependency scan
            assert scan_result['scan_status'] == 'completed'
            assert 'dependencies' in scan_result
            assert all(dep['vulnerabilities'] == [] for dep in scan_result['dependencies'])
            
            # Test dependency updates
            update_result = docker_client.images.update_dependencies(test_image.id)
            assert update_result['updated'] is True
            assert update_result['vulnerabilities_fixed'] >= 0
        finally:
            docker_client.images.remove(test_image.id)

@pytest.mark.security
@pytest.mark.container
class TestKubernetesSecurity:
    """Test Kubernetes security features."""

    def test_pod_security_context(self, k8s_client, security_test_client, security_config):
        """Test Kubernetes pod security context."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test pod security context
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': 'test-pod'
            },
            'spec': {
                'securityContext': {
                    'runAsNonRoot': True,
                    'runAsUser': 1000,
                    'runAsGroup': 3000,
                    'fsGroup': 2000
                },
                'containers': [{
                    'name': 'test-container',
                    'image': 'alpine:latest',
                    'securityContext': {
                        'allowPrivilegeEscalation': False,
                        'capabilities': {
                            'drop': ['ALL']
                        },
                        'readOnlyRootFilesystem': True
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
            
            # Verify pod security settings
            pod_info = k8s_client.read_namespaced_pod(
                name='test-pod',
                namespace='default'
            )
            
            assert pod_info.spec.security_context.run_as_non_root is True
            assert pod_info.spec.security_context.run_as_user == 1000
            assert pod_info.spec.security_context.run_as_group == 3000
            assert pod_info.spec.security_context.fs_group == 2000
        finally:
            k8s_client.delete_namespaced_pod(
                name='test-pod',
                namespace='default'
            )

    def test_network_policy(self, k8s_client, security_test_client, security_config):
        """Test Kubernetes network policy."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test network policy
        policy_manifest = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'NetworkPolicy',
            'metadata': {
                'name': 'test-policy'
            },
            'spec': {
                'podSelector': {
                    'matchLabels': {
                        'app': 'test'
                    }
                },
                'policyTypes': ['Ingress', 'Egress'],
                'ingress': [{
                    'from': [{
                        'podSelector': {
                            'matchLabels': {
                                'role': 'frontend'
                            }
                        }
                    }]
                }],
                'egress': [{
                    'to': [{
                        'podSelector': {
                            'matchLabels': {
                                'role': 'backend'
                            }
                        }
                    }]
                }]
            }
        }
        
        try:
            # Create network policy
            policy = k8s_client.create_namespaced_network_policy(
                namespace='default',
                body=policy_manifest
            )
            
            # Verify policy
            policy_info = k8s_client.read_namespaced_network_policy(
                name='test-policy',
                namespace='default'
            )
            
            assert policy_info.spec.pod_selector.match_labels['app'] == 'test'
            assert 'Ingress' in policy_info.spec.policy_types
            assert 'Egress' in policy_info.spec.policy_types
        finally:
            k8s_client.delete_namespaced_network_policy(
                name='test-policy',
                namespace='default'
            )

@pytest.mark.security
@pytest.mark.container
class TestContainerSecretsSecurity:
    """Test container secrets security features."""

    def test_secrets_management(self, docker_client, security_test_client, security_config):
        """Test container secrets management."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test Docker secrets
        secret = docker_client.secrets.create(
            name='test-secret',
            data='secret-data'
        )
        
        try:
            # Verify secret
            secret_info = docker_client.secrets.get(secret.id)
            assert secret_info.attrs['Spec']['Name'] == 'test-secret'
            
            # Test secret rotation
            rotate_response = client.post("/api/container/secrets/rotate", json={
                "secret_id": secret.id
            })
            
            assert rotate_response.status_code == 200
            assert rotate_response.json['rotated'] is True
        finally:
            secret.remove()

    def test_kubernetes_secrets(self, k8s_client, security_test_client, security_config):
        """Test Kubernetes secrets management."""
        client, _ = security_test_client()
        container_config = get_container_config()
        
        # Test Kubernetes secrets
        secret_manifest = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': 'test-secret'
            },
            'type': 'Opaque',
            'data': {
                'username': 'dGVzdA==',  # base64 encoded 'test'
                'password': 'cGFzc3dvcmQ='  # base64 encoded 'password'
            }
        }
        
        try:
            # Create secret
            secret = k8s_client.create_namespaced_secret(
                namespace='default',
                body=secret_manifest
            )
            
            # Verify secret
            secret_info = k8s_client.read_namespaced_secret(
                name='test-secret',
                namespace='default'
            )
            
            assert secret_info.data['username'] == 'dGVzdA=='
            assert secret_info.data['password'] == 'cGFzc3dvcmQ='
            
            # Test secret rotation
            rotate_response = client.post("/api/kubernetes/secrets/rotate", json={
                "secret_name": "test-secret",
                "namespace": "default"
            })
            
            assert rotate_response.status_code == 200
            assert rotate_response.json['rotated'] is True
        finally:
            k8s_client.delete_namespaced_secret(
                name='test-secret',
                namespace='default'
            ) 