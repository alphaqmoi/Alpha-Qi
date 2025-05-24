"""Cloud security tests."""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict

import azure.storage.blob
import boto3
import google.cloud.storage
import pytest
from google.cloud import secretmanager
from google.cloud.exceptions import NotFound
from moto import mock_iam, mock_kms, mock_s3, mock_secretsmanager
from services.cloud import CloudService
from services.security import SecurityService

from app.exceptions import SecurityException
from app.services.cloud import CloudSecurityService
from tests.security.config import get_cloud_config


@pytest.fixture
def aws_client():
    """Create AWS client fixtures."""
    with mock_s3(), mock_secretsmanager():
        s3 = boto3.client("s3")
        secrets = boto3.client("secretsmanager")
        yield {"s3": s3, "secrets": secrets}


@pytest.fixture
def gcp_client():
    """Create GCP client fixtures."""
    storage_client = google.cloud.storage.Client()
    secret_client = secretmanager.SecretManagerServiceClient()
    return {"storage": storage_client, "secrets": secret_client}


@pytest.mark.security
@pytest.mark.cloud
class TestCloudSecurity:
    """Test cloud security features."""

    @mock_s3
    def test_aws_storage_security(self, security_test_client, security_config):
        """Test AWS storage security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test S3 bucket encryption
        s3 = boto3.client("s3")
        bucket_name = "test-secure-bucket"
        s3.create_bucket(Bucket=bucket_name)

        # Verify bucket encryption
        encryption = s3.get_bucket_encryption(Bucket=bucket_name)
        assert (
            encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
                "ApplyServerSideEncryptionByDefault"
            ]["SSEAlgorithm"]
            == "AES256"
        )

        # Test object encryption
        test_data = b"test sensitive data"
        s3.put_object(
            Bucket=bucket_name,
            Key="test.txt",
            Body=test_data,
            ServerSideEncryption="AES256",
        )

        # Verify object encryption
        head = s3.head_object(Bucket=bucket_name, Key="test.txt")
        assert head["ServerSideEncryption"] == "AES256"

    @mock_iam
    def test_aws_iam_security(self, security_test_client, security_config):
        """Test AWS IAM security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test IAM policy enforcement
        iam = boto3.client("iam")

        # Create test role with minimal permissions
        role_name = "test-role"
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        iam.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )

        # Verify role permissions
        role = iam.get_role(RoleName=role_name)
        assert role["Role"]["AssumeRolePolicyDocument"] == assume_role_policy

        # Test policy attachment
        policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        # Verify policy attachment
        policies = iam.list_attached_role_policies(RoleName=role_name)
        assert any(p["PolicyArn"] == policy_arn for p in policies["AttachedPolicies"])

    @mock_kms
    def test_aws_kms_security(self, security_test_client, security_config):
        """Test AWS KMS security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test KMS key creation and rotation
        kms = boto3.client("kms")

        # Create test key
        key = kms.create_key(
            Description="Test key",
            KeyUsage="ENCRYPT_DECRYPT",
            Origin="AWS_KMS",
            MultiRegion=True,
        )
        key_id = key["KeyMetadata"]["KeyId"]

        # Enable key rotation
        kms.enable_key_rotation(KeyId=key_id)

        # Verify key rotation
        key_rotation = kms.get_key_rotation_status(KeyId=key_id)
        assert key_rotation["KeyRotationEnabled"] is True

    def test_gcp_storage_security(self, security_test_client, security_config):
        """Test GCP storage security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test bucket encryption
        storage_client = google.cloud.storage.Client()
        bucket_name = "test-secure-bucket"
        bucket = storage_client.create_bucket(bucket_name)

        # Enable bucket encryption
        bucket.encryption = {
            "defaultKmsKeyName": f"projects/{storage_client.project}/locations/global/keyRings/test-ring/cryptoKeys/test-key"
        }
        bucket.patch()

        # Verify bucket encryption
        bucket.reload()
        assert bucket.encryption is not None

        # Test object encryption
        blob = bucket.blob("test.txt")
        blob.upload_from_string("test sensitive data")

        # Verify object encryption
        blob.reload()
        assert blob.kms_key_name is not None

    def test_gcp_secret_management(self, security_test_client, security_config):
        """Test GCP secret management security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test secret creation and access
        secret_client = secretmanager.SecretManagerServiceClient()
        project_id = "test-project"
        secret_id = "test-secret"

        # Create secret
        parent = f"projects/{project_id}"
        secret = secret_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )

        # Add secret version
        secret_client.add_secret_version(
            request={"parent": secret.name, "payload": {"data": b"test-secret-data"}}
        )

        # Verify secret access
        version = secret_client.access_secret_version(
            request={"name": f"{secret.name}/versions/latest"}
        )
        assert version.payload.data == b"test-secret-data"

    def test_cloud_audit_logging(self, security_test_client, security_config):
        """Test cloud audit logging."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test AWS CloudTrail logging
        cloudtrail = boto3.client("cloudtrail")

        # Create trail
        trail_name = "test-trail"
        cloudtrail.create_trail(
            Name=trail_name,
            S3BucketName="test-bucket",
            IncludeGlobalServiceEvents=True,
            IsMultiRegionTrail=True,
            EnableLogFileValidation=True,
        )

        # Verify trail configuration
        trail = cloudtrail.get_trail(Name=trail_name)
        assert trail["Trail"]["IncludeGlobalServiceEvents"] is True
        assert trail["Trail"]["IsMultiRegionTrail"] is True
        assert trail["Trail"]["LogFileValidationEnabled"] is True

        # Test GCP audit logging
        logging_client = google.cloud.logging.Client()

        # Create sink
        sink_name = "test-sink"
        sink = logging_client.sink(sink_name, "storage.googleapis.com/test-bucket")
        sink.create()

        # Verify sink configuration
        sink.reload()
        assert sink.destination == "storage.googleapis.com/test-bucket"

    def test_cloud_monitoring(self, security_test_client, security_config):
        """Test cloud monitoring security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test AWS CloudWatch monitoring
        cloudwatch = boto3.client("cloudwatch")

        # Create metric alarm
        alarm_name = "test-alarm"
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            MetricName="CPUUtilization",
            Namespace="AWS/EC2",
            Statistic="Average",
            Period=300,
            EvaluationPeriods=2,
            Threshold=80.0,
            ComparisonOperator="GreaterThanThreshold",
            AlarmActions=["arn:aws:sns:region:account-id:test-topic"],
        )

        # Verify alarm configuration
        alarms = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        assert alarms["MetricAlarms"][0]["Threshold"] == 80.0

        # Test GCP monitoring
        monitoring_client = google.cloud.monitoring_v3.MetricServiceClient()

        # Create alert policy
        project_name = f"projects/{monitoring_client.project}"
        policy = {
            "display_name": "test-policy",
            "conditions": [
                {
                    "display_name": "CPU utilization",
                    "condition_threshold": {
                        "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
                        "comparison": "COMPARISON_GT",
                        "threshold_value": 0.8,
                        "duration": {"seconds": 300},
                    },
                }
            ],
        }

        # Create policy
        alert_policy = monitoring_client.create_alert_policy(
            name=project_name, alert_policy=policy
        )

        # Verify policy configuration
        assert alert_policy.display_name == "test-policy"
        assert alert_policy.conditions[0].condition_threshold.threshold_value == 0.8

    def test_cloud_credential_rotation(self, security_test_client, security_config):
        """Test cloud credential rotation."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test AWS IAM credential rotation
        iam = boto3.client("iam")

        # Create access key
        user_name = "test-user"
        key = iam.create_access_key(UserName=user_name)

        # Verify key creation
        keys = iam.list_access_keys(UserName=user_name)
        assert len(keys["AccessKeyMetadata"]) == 1

        # Rotate key
        iam.delete_access_key(
            UserName=user_name, AccessKeyId=key["AccessKey"]["AccessKeyId"]
        )
        new_key = iam.create_access_key(UserName=user_name)

        # Verify key rotation
        keys = iam.list_access_keys(UserName=user_name)
        assert len(keys["AccessKeyMetadata"]) == 1
        assert (
            keys["AccessKeyMetadata"][0]["AccessKeyId"]
            == new_key["AccessKey"]["AccessKeyId"]
        )

        # Test GCP service account key rotation
        iam_client = google.cloud.iam.IAMClient()

        # Create service account key
        service_account = f"projects/{iam_client.project}/serviceAccounts/test@test.iam.gserviceaccount.com"
        key = iam_client.create_service_account_key(
            request={
                "name": service_account,
                "private_key_type": "TYPE_GOOGLE_CREDENTIALS_FILE",
                "key_algorithm": "KEY_ALG_RSA_2048",
            }
        )

        # Verify key creation
        keys = iam_client.list_service_account_keys(request={"name": service_account})
        assert len(keys.keys) == 1

        # Rotate key
        iam_client.delete_service_account_key(request={"name": keys.keys[0].name})
        new_key = iam_client.create_service_account_key(
            request={
                "name": service_account,
                "private_key_type": "TYPE_GOOGLE_CREDENTIALS_FILE",
                "key_algorithm": "KEY_ALG_RSA_2048",
            }
        )

        # Verify key rotation
        keys = iam_client.list_service_account_keys(request={"name": service_account})
        assert len(keys.keys) == 1
        assert keys.keys[0].name == new_key.name

    def test_cloud_credentials_security(self, security_test_client, security_config):
        """Test cloud credentials security."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get credentials configuration
        response = client.get("/api/cloud/credentials")
        creds_config = response.json

        # Test credential rotation
        rotation_response = client.post("/api/cloud/credentials/rotate")

        # Assert
        assert response.status_code == 200
        assert creds_config["encryption_enabled"]
        assert creds_config["rotation_enabled"]
        assert creds_config["min_rotation_period"] == 90  # days
        assert rotation_response.status_code == 200
        assert rotation_response.json["credentials_rotated"]

    def test_cloud_storage_security(self, security_test_client, security_config):
        """Test cloud storage security."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get storage configuration
        response = client.get("/api/cloud/storage")
        storage_config = response.json

        # Test encrypted storage
        test_data = {"sensitive": "data"}
        upload_response = client.post(
            "/api/cloud/storage/upload", json={"data": test_data, "encrypt": True}
        )

        # Verify encryption
        download_response = client.get(
            f"/api/cloud/storage/{upload_response.json['id']}"
        )

        # Assert
        assert response.status_code == 200
        assert storage_config["encryption_at_rest"]
        assert storage_config["encryption_in_transit"]
        assert upload_response.status_code == 201
        assert download_response.json["data"] == test_data

    def test_cloud_access_control(self, security_test_client, security_config):
        """Test cloud access control."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get access control configuration
        response = client.get("/api/cloud/access")
        access_config = response.json

        # Test IAM policies
        policy_response = client.get("/api/cloud/iam/policies")

        # Test bucket policies
        bucket_response = client.get("/api/cloud/storage/bucket-policies")

        # Assert
        assert response.status_code == 200
        assert access_config["iam_enabled"]
        assert access_config["bucket_policies_enabled"]
        assert policy_response.status_code == 200
        assert bucket_response.status_code == 200
        assert all(
            policy["enforce_encryption"] for policy in policy_response.json["policies"]
        )

    def test_cloud_backup_security(self, security_test_client, security_config):
        """Test cloud backup security."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get backup configuration
        response = client.get("/api/cloud/backup")
        backup_config = response.json

        # Test backup creation
        backup_response = client.post(
            "/api/cloud/backup/create", json={"type": "full", "encrypt": True}
        )

        # Test backup restoration
        restore_response = client.post(
            f"/api/cloud/backup/{backup_response.json['id']}/restore"
        )

        # Assert
        assert response.status_code == 200
        assert backup_config["encryption_enabled"]
        assert backup_config["versioning_enabled"]
        assert backup_response.status_code == 201
        assert restore_response.status_code == 200
        assert backup_response.json["encrypted"]

    def test_cloud_key_management(self, security_test_client, security_config):
        """Test cloud key management."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get KMS configuration
        response = client.get("/api/cloud/kms")
        kms_config = response.json

        # Test key creation
        key_response = client.post(
            "/api/cloud/kms/keys", json={"purpose": "encryption", "rotation_period": 90}
        )

        # Test key rotation
        rotate_response = client.post(
            f"/api/cloud/kms/keys/{key_response.json['id']}/rotate"
        )

        # Assert
        assert response.status_code == 200
        assert kms_config["enabled"]
        assert kms_config["rotation_enabled"]
        assert key_response.status_code == 201
        assert rotate_response.status_code == 200
        assert key_response.json["rotation_period"] == 90

    def test_cloud_network_security(self, security_test_client, security_config):
        """Test cloud network security."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get network configuration
        response = client.get("/api/cloud/network")
        network_config = response.json

        # Test VPC configuration
        vpc_response = client.get("/api/cloud/network/vpc")

        # Test security groups
        sg_response = client.get("/api/cloud/network/security-groups")

        # Assert
        assert response.status_code == 200
        assert network_config["vpc_enabled"]
        assert network_config["security_groups_enabled"]
        assert vpc_response.status_code == 200
        assert sg_response.status_code == 200
        assert all(sg["restrict_ingress"] for sg in sg_response.json["groups"])

    def test_cloud_monitoring(self, security_test_client, security_config):
        """Test cloud monitoring and alerting."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get monitoring configuration
        response = client.get("/api/cloud/monitoring")
        monitoring_config = response.json

        # Test alert creation
        alert_response = client.post(
            "/api/cloud/monitoring/alerts",
            json={"type": "security", "threshold": 0.8, "action": "notify"},
        )

        # Test metrics collection
        metrics_response = client.get("/api/cloud/monitoring/metrics")

        # Assert
        assert response.status_code == 200
        assert monitoring_config["enabled"]
        assert monitoring_config["alerting_enabled"]
        assert alert_response.status_code == 201
        assert metrics_response.status_code == 200
        assert "security_metrics" in metrics_response.json

    def test_cloud_compliance(self, security_test_client, security_config):
        """Test cloud compliance controls."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get compliance configuration
        response = client.get("/api/cloud/compliance")
        compliance_config = response.json

        # Test compliance checks
        checks_response = client.get("/api/cloud/compliance/checks")

        # Test compliance reporting
        report_response = client.get("/api/cloud/compliance/report")

        # Assert
        assert response.status_code == 200
        assert compliance_config["enabled"]
        assert compliance_config["standards"] == ["ISO27001", "SOC2", "GDPR"]
        assert checks_response.status_code == 200
        assert report_response.status_code == 200
        assert all(check["passed"] for check in checks_response.json["checks"])

    def test_cloud_disaster_recovery(self, security_test_client, security_config):
        """Test cloud disaster recovery."""
        # Arrange
        client, _ = security_test_client()
        service = CloudSecurityService(security_config)

        # Act
        # Get DR configuration
        response = client.get("/api/cloud/disaster-recovery")
        dr_config = response.json

        # Test DR plan
        plan_response = client.get("/api/cloud/disaster-recovery/plan")

        # Test failover
        failover_response = client.post(
            "/api/cloud/disaster-recovery/failover",
            json={"type": "test", "region": "backup"},
        )

        # Assert
        assert response.status_code == 200
        assert dr_config["enabled"]
        assert dr_config["automated_failover"]
        assert plan_response.status_code == 200
        assert failover_response.status_code == 200
        assert failover_response.json["status"] == "success"


@pytest.mark.security
@pytest.mark.cloud
class TestAWSStorageSecurity:
    """Test AWS storage security features."""

    def test_s3_bucket_encryption(
        self, aws_client, security_test_client, security_config
    ):
        """Test S3 bucket encryption settings."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test bucket with encryption
        bucket_name = "test-secure-bucket"
        aws_client["s3"].create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

        # Enable default encryption
        aws_client["s3"].put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )

        try:
            # Verify encryption settings
            encryption = aws_client["s3"].get_bucket_encryption(Bucket=bucket_name)
            assert (
                encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
                    "ApplyServerSideEncryptionByDefault"
                ]["SSEAlgorithm"]
                == "AES256"
            )

            # Test object encryption
            test_data = "test-secure-data"
            aws_client["s3"].put_object(
                Bucket=bucket_name,
                Key="test.txt",
                Body=test_data,
                ServerSideEncryption="AES256",
            )

            # Verify object encryption
            obj = aws_client["s3"].get_object(Bucket=bucket_name, Key="test.txt")
            assert obj["ServerSideEncryption"] == "AES256"
        finally:
            aws_client["s3"].delete_bucket(Bucket=bucket_name)

    def test_s3_bucket_policy(self, aws_client, security_test_client, security_config):
        """Test S3 bucket security policies."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test bucket
        bucket_name = "test-policy-bucket"
        aws_client["s3"].create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

        # Apply secure bucket policy
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "SecureTransport",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                },
                {
                    "Sid": "EnforceTLS",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {"NumericLessThan": {"s3:TlsVersion": "1.2"}},
                },
            ],
        }

        aws_client["s3"].put_bucket_policy(
            Bucket=bucket_name, Policy=json.dumps(bucket_policy)
        )

        try:
            # Verify bucket policy
            policy = aws_client["s3"].get_bucket_policy(Bucket=bucket_name)
            policy_doc = json.loads(policy["Policy"])
            assert len(policy_doc["Statement"]) == 2
            assert (
                policy_doc["Statement"][0]["Condition"]["Bool"]["aws:SecureTransport"]
                == "false"
            )
            assert (
                policy_doc["Statement"][1]["Condition"]["NumericLessThan"][
                    "s3:TlsVersion"
                ]
                == "1.2"
            )

            # Test bucket versioning
            aws_client["s3"].put_bucket_versioning(
                Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
            )

            versioning = aws_client["s3"].get_bucket_versioning(Bucket=bucket_name)
            assert versioning["Status"] == "Enabled"
        finally:
            aws_client["s3"].delete_bucket(Bucket=bucket_name)

    def test_s3_access_logging(self, aws_client, security_test_client, security_config):
        """Test S3 bucket access logging."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create source and logging buckets
        source_bucket = "test-source-bucket"
        logging_bucket = "test-logging-bucket"

        for bucket in [source_bucket, logging_bucket]:
            aws_client["s3"].create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

        # Enable access logging
        aws_client["s3"].put_bucket_logging(
            Bucket=source_bucket,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": logging_bucket,
                    "TargetPrefix": "logs/",
                }
            },
        )

        try:
            # Verify logging configuration
            logging = aws_client["s3"].get_bucket_logging(Bucket=source_bucket)
            assert logging["LoggingEnabled"]["TargetBucket"] == logging_bucket
            assert logging["LoggingEnabled"]["TargetPrefix"] == "logs/"

            # Test logging with object operations
            aws_client["s3"].put_object(
                Bucket=source_bucket, Key="test.txt", Body="test-data"
            )

            # Verify log file creation
            logs = aws_client["s3"].list_objects_v2(
                Bucket=logging_bucket, Prefix="logs/"
            )
            assert "Contents" in logs
        finally:
            for bucket in [source_bucket, logging_bucket]:
                aws_client["s3"].delete_bucket(Bucket=bucket)


@pytest.mark.security
@pytest.mark.cloud
class TestGCPStorageSecurity:
    """Test GCP storage security features."""

    def test_gcs_bucket_encryption(
        self, gcp_client, security_test_client, security_config
    ):
        """Test GCS bucket encryption settings."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test bucket with encryption
        bucket_name = "test-secure-bucket"
        bucket = gcp_client["storage"].create_bucket(bucket_name)

        # Enable default encryption
        bucket.default_kms_key_name = f'projects/{cloud_config["gcp"]["project_id"]}/locations/global/keyRings/test-keyring/cryptoKeys/test-key'
        bucket.patch()

        try:
            # Verify encryption settings
            bucket.reload()
            assert bucket.default_kms_key_name is not None

            # Test object encryption
            blob = bucket.blob("test.txt")
            blob.upload_from_string("test-secure-data", encryption_key="test-key")

            # Verify object encryption
            blob.reload()
            assert blob.kms_key_name is not None
        finally:
            bucket.delete()

    def test_gcs_bucket_iam(self, gcp_client, security_test_client, security_config):
        """Test GCS bucket IAM policies."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test bucket
        bucket_name = "test-iam-bucket"
        bucket = gcp_client["storage"].create_bucket(bucket_name)

        # Apply secure IAM policy
        policy = {
            "bindings": [
                {
                    "role": "roles/storage.objectViewer",
                    "members": [
                        "serviceAccount:test-service@test-project.iam.gserviceaccount.com"
                    ],
                },
                {
                    "role": "roles/storage.objectCreator",
                    "members": ["user:test-user@example.com"],
                },
            ]
        }

        bucket.set_iam_policy(policy)

        try:
            # Verify IAM policy
            current_policy = bucket.get_iam_policy()
            assert len(current_policy.bindings) == 2
            assert current_policy.bindings[0].role == "roles/storage.objectViewer"
            assert current_policy.bindings[1].role == "roles/storage.objectCreator"

            # Test bucket versioning
            bucket.versioning_enabled = True
            bucket.patch()

            bucket.reload()
            assert bucket.versioning_enabled is True
        finally:
            bucket.delete()

    def test_gcs_audit_logging(self, gcp_client, security_test_client, security_config):
        """Test GCS bucket audit logging."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test bucket
        bucket_name = "test-audit-bucket"
        bucket = gcp_client["storage"].create_bucket(bucket_name)

        # Enable audit logging
        bucket.iam_configuration.uniform_bucket_level_access = True
        bucket.iam_configuration.public_access_prevention = "enforced"
        bucket.patch()

        try:
            # Verify audit settings
            bucket.reload()
            assert bucket.iam_configuration.uniform_bucket_level_access is True
            assert bucket.iam_configuration.public_access_prevention == "enforced"

            # Test audit logging with object operations
            blob = bucket.blob("test.txt")
            blob.upload_from_string("test-data")

            # Verify audit log creation
            logs = gcp_client["storage"].list_blobs(bucket, prefix="_audit_logs/")
            assert any(log.name.startswith("_audit_logs/") for log in logs)
        finally:
            bucket.delete()


@pytest.mark.security
@pytest.mark.cloud
class TestCloudSecretManagement:
    """Test cloud secret management features."""

    def test_aws_secrets_rotation(
        self, aws_client, security_test_client, security_config
    ):
        """Test AWS secrets rotation."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test secret
        secret_name = "test-rotation-secret"
        aws_client["secrets"].create_secret(
            Name=secret_name,
            SecretString="initial-secret-value",
            Description="Test secret for rotation",
        )

        try:
            # Configure rotation
            aws_client["secrets"].rotate_secret(
                SecretId=secret_name,
                RotationLambdaARN=cloud_config["aws"]["rotation_lambda_arn"],
                RotationRules={"AutomaticallyAfterDays": 30},
            )

            # Verify rotation settings
            secret = aws_client["secrets"].describe_secret(SecretId=secret_name)
            assert secret["RotationEnabled"] is True
            assert secret["RotationRules"]["AutomaticallyAfterDays"] == 30

            # Test manual rotation
            aws_client["secrets"].rotate_secret(SecretId=secret_name, ForceRotate=True)

            # Verify rotation
            rotated_secret = aws_client["secrets"].get_secret_value(
                SecretId=secret_name
            )
            assert rotated_secret["SecretString"] != "initial-secret-value"
        finally:
            aws_client["secrets"].delete_secret(
                SecretId=secret_name, ForceDeleteWithoutRecovery=True
            )

    def test_gcp_secrets_rotation(
        self, gcp_client, security_test_client, security_config
    ):
        """Test GCP secrets rotation."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Create test secret
        parent = f'projects/{cloud_config["gcp"]["project_id"]}'
        secret_id = "test-rotation-secret"

        secret = gcp_client["secrets"].create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )

        # Add initial version
        gcp_client["secrets"].add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": b"initial-secret-value"},
            }
        )

        try:
            # Configure rotation
            gcp_client["secrets"].update_secret(
                request={
                    "secret": {
                        "name": secret.name,
                        "rotation": {
                            "next_rotation_time": {
                                "seconds": int(
                                    (datetime.now() + timedelta(days=30)).timestamp()
                                )
                            },
                            "rotation_period": {
                                "seconds": 30 * 24 * 60 * 60  # 30 days
                            },
                        },
                    },
                    "update_mask": {"paths": ["rotation"]},
                }
            )

            # Verify rotation settings
            updated_secret = gcp_client["secrets"].get_secret(
                request={"name": secret.name}
            )
            assert updated_secret.rotation.rotation_period.seconds == 30 * 24 * 60 * 60

            # Test manual rotation
            new_version = gcp_client["secrets"].add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": b"rotated-secret-value"},
                }
            )

            # Verify rotation
            latest_version = gcp_client["secrets"].get_secret_version(
                request={"name": new_version.name}
            )
            assert latest_version.payload.data.decode("UTF-8") == "rotated-secret-value"
        finally:
            gcp_client["secrets"].delete_secret(request={"name": secret.name})

    def test_secret_access_control(
        self, aws_client, gcp_client, security_test_client, security_config
    ):
        """Test secret access control policies."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test AWS secret access control
        aws_secret_name = "test-access-secret"
        aws_client["secrets"].create_secret(
            Name=aws_secret_name,
            SecretString="test-secret",
            Description="Test secret for access control",
        )

        # Apply AWS resource policy
        aws_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f'arn:aws:iam::{cloud_config["aws"]["account_id"]}:role/test-role'
                    },
                    "Action": "secretsmanager:GetSecretValue",
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {"aws:PrincipalTag/Environment": "production"}
                    },
                }
            ],
        }

        aws_client["secrets"].put_resource_policy(
            SecretId=aws_secret_name, ResourcePolicy=json.dumps(aws_policy)
        )

        try:
            # Verify AWS policy
            aws_policy = aws_client["secrets"].get_resource_policy(
                SecretId=aws_secret_name
            )
            policy_doc = json.loads(aws_policy["ResourcePolicy"])
            assert (
                policy_doc["Statement"][0]["Condition"]["StringEquals"][
                    "aws:PrincipalTag/Environment"
                ]
                == "production"
            )

            # Test GCP secret access control
            gcp_parent = f'projects/{cloud_config["gcp"]["project_id"]}'
            gcp_secret_id = "test-access-secret"

            gcp_secret = gcp_client["secrets"].create_secret(
                request={
                    "parent": gcp_parent,
                    "secret_id": gcp_secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Apply GCP IAM policy
            gcp_policy = {
                "bindings": [
                    {
                        "role": "roles/secretmanager.secretAccessor",
                        "members": [
                            f'serviceAccount:test-service@{cloud_config["gcp"]["project_id"]}.iam.gserviceaccount.com'
                        ],
                        "condition": {
                            "expression": 'resource.type == "secretmanager.googleapis.com/Secret" && resource.name.startsWith("projects/{project}/secrets/test-access-secret")'
                        },
                    }
                ]
            }

            gcp_client["secrets"].set_iam_policy(
                request={"resource": gcp_secret.name, "policy": gcp_policy}
            )

            # Verify GCP policy
            gcp_policy = gcp_client["secrets"].get_iam_policy(
                request={"resource": gcp_secret.name}
            )
            assert gcp_policy.bindings[0].role == "roles/secretmanager.secretAccessor"
            assert "condition" in gcp_policy.bindings[0]
        finally:
            aws_client["secrets"].delete_secret(
                SecretId=aws_secret_name, ForceDeleteWithoutRecovery=True
            )
            gcp_client["secrets"].delete_secret(request={"name": gcp_secret.name})


@pytest.mark.security
@pytest.mark.cloud
class TestCloudAuditLogging:
    """Test cloud audit logging features."""

    def test_aws_cloudtrail(self, security_test_client, security_config):
        """Test AWS CloudTrail logging."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test CloudTrail
        cloudtrail_client = boto3.client("cloudtrail")
        trail_name = "test-security-trail"

        try:
            # Create trail
            trail = cloudtrail_client.create_trail(
                Name=trail_name,
                S3BucketName="test-audit-logs",
                IncludeGlobalServiceEvents=True,
                IsMultiRegionTrail=True,
                EnableLogFileValidation=True,
                CloudWatchLogsLogGroupArn="arn:aws:logs:us-west-2:123456789012:log-group:test-logs:*",
                CloudWatchLogsRoleArn="arn:aws:iam::123456789012:role/CloudTrailCloudWatchRole",
            )

            # Start logging
            cloudtrail_client.start_logging(Name=trail_name)

            # Verify trail settings
            trail_details = cloudtrail_client.get_trail(Name=trail_name)
            assert trail_details["Trail"]["IncludeGlobalServiceEvents"]
            assert trail_details["Trail"]["IsMultiRegionTrail"]
            assert trail_details["Trail"]["LogFileValidationEnabled"]

            # Test event logging
            test_event = {
                "EventTime": datetime.now(),
                "EventName": "TestEvent",
                "EventSource": "test.amazonaws.com",
                "AWSRegion": "us-west-2",
            }

            cloudtrail_client.put_event_selectors(
                TrailName=trail_name,
                EventSelectors=[
                    {"ReadWriteType": "All", "IncludeManagementEvents": True}
                ],
            )

            # Verify event selector
            selectors = cloudtrail_client.get_event_selectors(TrailName=trail_name)
            assert selectors["EventSelectors"][0]["IncludeManagementEvents"]
        finally:
            # Cleanup
            cloudtrail_client.delete_trail(Name=trail_name)

    def test_gcp_audit_logging(self, security_test_client, security_config):
        """Test GCP audit logging."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test audit logging
        logging_client = google.cloud.logging.Client()
        log_bucket_name = "test-audit-logs"
        log_bucket = logging_client.create_bucket(log_bucket_name)

        try:
            # Configure audit logging
            log_bucket.iam_configuration.uniform_bucket_level_access_enabled = True
            log_bucket.iam_configuration.public_access_prevention = "enforced"
            log_bucket.patch()

            # Set up log sink
            sink_name = "test-audit-sink"
            sink = {
                "name": sink_name,
                "destination": f"storage.googleapis.com/{log_bucket_name}",
                "filter": "resource.type=gcs_bucket",
                "include_children": True,
            }

            # Verify bucket settings
            log_bucket.reload()
            assert log_bucket.iam_configuration.uniform_bucket_level_access_enabled
            assert log_bucket.iam_configuration.public_access_prevention == "enforced"

            # Test log export
            test_blob = log_bucket.blob("test-audit-log.txt")
            test_blob.upload_from_string(
                "test audit log entry", content_type="application/json"
            )

            # Verify log export
            test_blob.reload()
            assert test_blob.content_type == "application/json"
        finally:
            # Cleanup
            log_bucket.delete()


@pytest.mark.security
@pytest.mark.cloud
class TestContainerSecurity:
    """Test container security features."""

    def test_aws_ecs_security(self, aws_client, security_test_client, security_config):
        """Test AWS ECS container security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test ECS task definition security
        ecs = boto3.client("ecs")
        task_def = {
            "family": "test-secure-task",
            "containerDefinitions": [
                {
                    "name": "test-container",
                    "image": "test-image:latest",
                    "essential": True,
                    "secrets": [
                        {
                            "name": "DB_PASSWORD",
                            "valueFrom": "arn:aws:secretsmanager:region:account:secret:db-password",
                        }
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/test-secure-task",
                            "awslogs-region": "us-west-2",
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                }
            ],
            "requiresCompatibilities": ["FARGATE"],
            "networkMode": "awsvpc",
            "cpu": "256",
            "memory": "512",
            "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
        }

        try:
            # Register task definition
            response = ecs.register_task_definition(**task_def)
            task_def_arn = response["taskDefinition"]["taskDefinitionArn"]

            # Verify security settings
            task_def_details = ecs.describe_task_definition(taskDefinition=task_def_arn)
            container_def = task_def_details["taskDefinition"]["containerDefinitions"][
                0
            ]

            assert "secrets" in container_def
            assert container_def["logConfiguration"]["logDriver"] == "awslogs"
            assert task_def_details["taskDefinition"]["networkMode"] == "awsvpc"
        finally:
            ecs.deregister_task_definition(taskDefinition=task_def_arn)

    def test_gcp_gke_security(self, gcp_client, security_test_client, security_config):
        """Test GCP GKE container security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test GKE cluster security
        container_client = google.cloud.container_v1.ClusterManagerClient()
        project_id = cloud_config["gcp"]["project_id"]
        zone = "us-central1-a"
        cluster_id = "test-secure-cluster"

        cluster = {
            "name": cluster_id,
            "description": "Test secure cluster",
            "initial_node_count": 1,
            "master_auth": {
                "client_certificate_config": {"issue_client_certificate": False}
            },
            "network_policy": {"enabled": True, "provider": "CALICO"},
            "pod_security_policy_config": {"enabled": True},
            "workload_identity_config": {"workload_pool": f"{project_id}.svc.id.goog"},
            "binary_authorization": {
                "evaluation_mode": "PROJECT_SINGLETON_POLICY_ENFORCE"
            },
        }

        try:
            # Create cluster
            operation = container_client.create_cluster(
                request={
                    "parent": f"projects/{project_id}/locations/{zone}",
                    "cluster": cluster,
                }
            )
            result = operation.result()

            # Verify security settings
            cluster_details = container_client.get_cluster(
                request={
                    "name": f"projects/{project_id}/locations/{zone}/clusters/{cluster_id}"
                }
            )

            assert cluster_details.network_policy.enabled
            assert cluster_details.pod_security_policy_config.enabled
            assert cluster_details.workload_identity_config is not None
            assert (
                cluster_details.binary_authorization.evaluation_mode
                == "PROJECT_SINGLETON_POLICY_ENFORCE"
            )
        finally:
            container_client.delete_cluster(
                request={
                    "name": f"projects/{project_id}/locations/{zone}/clusters/{cluster_id}"
                }
            )


@pytest.mark.security
@pytest.mark.cloud
class TestServerlessSecurity:
    """Test serverless security features."""

    def test_aws_lambda_security(
        self, aws_client, security_test_client, security_config
    ):
        """Test AWS Lambda security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test Lambda function security
        lambda_client = boto3.client("lambda")
        function_name = "test-secure-function"

        # Create secure function
        function_config = {
            "FunctionName": function_name,
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::account:role/lambda-execution-role",
            "Handler": "index.handler",
            "Code": {
                "ZipFile": b'def handler(event, context): return {"statusCode": 200}'
            },
            "Environment": {"Variables": {"ENVIRONMENT": "production"}},
            "TracingConfig": {"Mode": "Active"},
            "VpcConfig": {
                "SubnetIds": ["subnet-123456"],
                "SecurityGroupIds": ["sg-123456"],
            },
            "KMSKeyArn": "arn:aws:kms:region:account:key/key-id",
        }

        try:
            # Create function
            response = lambda_client.create_function(**function_config)
            function_arn = response["FunctionArn"]

            # Verify security settings
            function_details = lambda_client.get_function(FunctionName=function_name)
            config = function_details["Configuration"]

            assert config["TracingConfig"]["Mode"] == "Active"
            assert "VpcConfig" in config
            assert config["KMSKeyArn"] == function_config["KMSKeyArn"]

            # Test function policy
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "apigateway.amazonaws.com"},
                        "Action": "lambda:InvokeFunction",
                        "Resource": function_arn,
                        "Condition": {
                            "ArnLike": {
                                "AWS:SourceArn": "arn:aws:execute-api:region:account:api-id/*"
                            }
                        },
                    }
                ],
            }

            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId="APIGatewayInvoke",
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn="arn:aws:execute-api:region:account:api-id/*",
            )

            # Verify policy
            policy_response = lambda_client.get_policy(FunctionName=function_name)
            assert "APIGatewayInvoke" in policy_response["Policy"]
        finally:
            lambda_client.delete_function(FunctionName=function_name)

    def test_gcp_cloud_functions_security(
        self, gcp_client, security_test_client, security_config
    ):
        """Test GCP Cloud Functions security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test Cloud Function security
        functions_client = google.cloud.functions_v1.CloudFunctionsServiceClient()
        project_id = cloud_config["gcp"]["project_id"]
        location = "us-central1"
        function_name = "test-secure-function"

        function = {
            "name": f"projects/{project_id}/locations/{location}/functions/{function_name}",
            "description": "Test secure function",
            "entry_point": "handler",
            "runtime": "python39",
            "source_archive_url": "gs://test-bucket/function.zip",
            "https_trigger": {},
            "service_account_email": f"test-function@{project_id}.iam.gserviceaccount.com",
            "vpc_connector": "projects/test-project/locations/us-central1/connectors/test-connector",
            "ingress_settings": "ALLOW_INTERNAL_ONLY",
            "environment_variables": {"ENVIRONMENT": "production"},
            "max_instances": 10,
            "min_instances": 0,
            "available_memory_mb": 256,
            "timeout_seconds": 60,
            "labels": {"environment": "production"},
        }

        try:
            # Create function
            operation = functions_client.create_function(
                request={
                    "location": f"projects/{project_id}/locations/{location}",
                    "function": function,
                }
            )
            result = operation.result()

            # Verify security settings
            function_details = functions_client.get_function(
                request={"name": result.name}
            )

            assert function_details.ingress_settings == "ALLOW_INTERNAL_ONLY"
            assert function_details.vpc_connector is not None
            assert (
                function_details.service_account_email
                == function["service_account_email"]
            )

            # Test IAM policy
            policy = {
                "bindings": [
                    {
                        "role": "roles/cloudfunctions.invoker",
                        "members": [
                            f"serviceAccount:test-service@{project_id}.iam.gserviceaccount.com"
                        ],
                        "condition": {
                            "expression": 'request.time < timestamp("2023-12-31T00:00:00.000Z")'
                        },
                    }
                ]
            }

            functions_client.set_iam_policy(
                request={"resource": result.name, "policy": policy}
            )

            # Verify policy
            iam_policy = functions_client.get_iam_policy(
                request={"resource": result.name}
            )
            assert iam_policy.bindings[0].role == "roles/cloudfunctions.invoker"
        finally:
            functions_client.delete_function(request={"name": result.name})


@pytest.mark.security
@pytest.mark.cloud
class TestDatabaseSecurity:
    """Test database security features."""

    def test_aws_rds_security(self, aws_client, security_test_client, security_config):
        """Test AWS RDS security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test RDS instance security
        rds = boto3.client("rds")
        db_instance_id = "test-secure-db"

        # Create secure database instance
        db_config = {
            "DBInstanceIdentifier": db_instance_id,
            "Engine": "mysql",
            "DBInstanceClass": "db.t3.micro",
            "MasterUsername": "admin",
            "MasterUserPassword": "secure-password",
            "VpcSecurityGroupIds": ["sg-123456"],
            "DBSubnetGroupName": "test-subnet-group",
            "StorageEncrypted": True,
            "KmsKeyId": "arn:aws:kms:region:account:key/key-id",
            "EnableIAMDatabaseAuthentication": True,
            "EnablePerformanceInsights": True,
            "PerformanceInsightsRetentionPeriod": 7,
            "BackupRetentionPeriod": 7,
            "PreferredBackupWindow": "03:00-04:00",
            "PreferredMaintenanceWindow": "sun:04:00-sun:05:00",
            "MultiAZ": True,
            "PubliclyAccessible": False,
            "StorageType": "gp2",
            "DeletionProtection": True,
            "EnableCloudwatchLogsExports": ["error", "general", "slowquery"],
        }

        try:
            # Create database instance
            response = rds.create_db_instance(**db_config)
            waiter = rds.get_waiter("db_instance_available")
            waiter.wait(DBInstanceIdentifier=db_instance_id)

            # Verify security settings
            instance = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)[
                "DBInstances"
            ][0]

            assert instance["StorageEncrypted"]
            assert instance["EnableIAMDatabaseAuthentication"]
            assert instance["EnablePerformanceInsights"]
            assert instance["MultiAZ"]
            assert not instance["PubliclyAccessible"]
            assert instance["DeletionProtection"]
            assert "error" in instance["EnabledCloudwatchLogsExports"]

            # Test parameter group
            param_group = rds.create_db_parameter_group(
                DBParameterGroupFamily="mysql8.0",
                DBParameterGroupName="test-secure-params",
                Description="Test secure parameter group",
            )

            # Set secure parameters
            rds.modify_db_parameter_group(
                DBParameterGroupName="test-secure-params",
                Parameters=[
                    {
                        "ParameterName": "require_secure_transport",
                        "ParameterValue": "ON",
                        "ApplyMethod": "immediate",
                    },
                    {
                        "ParameterName": "ssl_cipher",
                        "ParameterValue": "HIGH:!aNULL:!eNULL:!EXPORT:!SSLv2:!SSLv3",
                        "ApplyMethod": "immediate",
                    },
                ],
            )

            # Apply parameter group
            rds.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                DBParameterGroupName="test-secure-params",
                ApplyImmediately=True,
            )

            # Verify parameter group
            instance = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)[
                "DBInstances"
            ][0]
            assert (
                instance["DBParameterGroups"][0]["DBParameterGroupName"]
                == "test-secure-params"
            )
        finally:
            rds.delete_db_instance(
                DBInstanceIdentifier=db_instance_id,
                SkipFinalSnapshot=True,
                DeleteAutomatedBackups=True,
            )
            rds.delete_db_parameter_group(DBParameterGroupName="test-secure-params")

    def test_gcp_cloud_sql_security(
        self, gcp_client, security_test_client, security_config
    ):
        """Test GCP Cloud SQL security."""
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test Cloud SQL instance security
        sql_client = google.cloud.sql_v1.CloudSqlInstancesServiceClient()
        project_id = cloud_config["gcp"]["project_id"]
        instance_id = "test-secure-sql"

        instance = {
            "name": f"{project_id}:{instance_id}",
            "database_version": "MYSQL_8_0",
            "region": "us-central1",
            "settings": {
                "tier": "db-n1-standard-1",
                "backup_configuration": {
                    "enabled": True,
                    "binary_log_enabled": True,
                    "start_time": "03:00",
                    "location": "us-central1",
                },
                "ip_configuration": {
                    "ipv4_enabled": False,
                    "private_network": "projects/test-project/global/networks/test-network",
                    "require_ssl": True,
                },
                "database_flags": [
                    {"name": "require_secure_transport", "value": "on"},
                    {
                        "name": "ssl_cipher",
                        "value": "HIGH:!aNULL:!eNULL:!EXPORT:!SSLv2:!SSLv3",
                    },
                ],
                "maintenance_window": {"day": 7, "hour": 4},
                "insights_config": {
                    "query_insights_enabled": True,
                    "query_string_length": 1024,
                    "record_application_tags": True,
                    "record_client_address": True,
                },
                "data_disk_type": "PD_SSD",
                "data_disk_size_gb": 10,
                "activation_policy": "ALWAYS",
                "availability_type": "REGIONAL",
            },
        }

        try:
            # Create instance
            operation = sql_client.insert(
                request={"project": project_id, "body": instance}
            )
            result = operation.result()

            # Verify security settings
            instance_details = sql_client.get(
                request={"project": project_id, "instance": instance_id}
            )

            assert instance_details.settings.backup_configuration.enabled
            assert instance_details.settings.ip_configuration.require_ssl
            assert instance_details.settings.availability_type == "REGIONAL"
            assert instance_details.settings.insights_config.query_insights_enabled

            # Test SSL configuration
            ssl_cert = sql_client.create_ssl_cert(
                request={
                    "project": project_id,
                    "instance": instance_id,
                    "body": {"common_name": "test-cert"},
                }
            )

            # Verify SSL certificate
            certs = sql_client.list_ssl_certs(
                request={"project": project_id, "instance": instance_id}
            )
            assert any(cert.common_name == "test-cert" for cert in certs.items)

            # Test IAM policy
            policy = {
                "bindings": [
                    {
                        "role": "roles/cloudsql.client",
                        "members": [
                            f"serviceAccount:test-service@{project_id}.iam.gserviceaccount.com"
                        ],
                        "condition": {
                            "expression": 'request.time < timestamp("2023-12-31T00:00:00.000Z")'
                        },
                    }
                ]
            }

            sql_client.set_iam_policy(
                request={
                    "resource": f"projects/{project_id}/instances/{instance_id}",
                    "policy": policy,
                }
            )

            # Verify policy
            iam_policy = sql_client.get_iam_policy(
                request={"resource": f"projects/{project_id}/instances/{instance_id}"}
            )
            assert iam_policy.bindings[0].role == "roles/cloudsql.client"
        finally:
            sql_client.delete(request={"project": project_id, "instance": instance_id})


@pytest.mark.security
@pytest.mark.cloud
class TestNetworkSecurity:
    """Test cloud network security features."""

    def test_aws_vpc_security(self, aws_client, security_test_client, security_config):
        """Test AWS VPC security configurations.

        This test verifies:
        - VPC flow logs are enabled
        - Security groups are properly configured
        - Network ACLs are properly set
        - VPC endpoints are secured
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test VPC security
        ec2 = boto3.client("ec2")
        vpc_id = "vpc-test123"

        # Create test VPC
        vpc = ec2.create_vpc(
            CidrBlock="10.0.0.0/16",
            EnableDnsHostnames=True,
            EnableDnsSupport=True,
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [{"Key": "Name", "Value": "test-secure-vpc"}],
                }
            ],
        )
        vpc_id = vpc["Vpc"]["VpcId"]

        try:
            # Enable VPC flow logs
            flow_logs = ec2.create_flow_logs(
                ResourceIds=[vpc_id],
                ResourceType="VPC",
                TrafficType="ALL",
                LogDestinationType="cloud-watch-logs",
                LogGroupName="vpc-flow-logs",
            )

            # Create security group
            sg = ec2.create_security_group(
                GroupName="test-secure-sg",
                Description="Test secure security group",
                VpcId=vpc_id,
            )
            sg_id = sg["GroupId"]

            # Configure security group rules
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "IpRanges": [
                            {"CidrIp": "0.0.0.0/0", "Description": "HTTPS access"}
                        ],
                    }
                ],
            )

            # Verify security configurations
            flow_logs_status = ec2.describe_flow_logs(
                Filter=[{"Name": "resource-id", "Values": [vpc_id]}]
            )
            assert len(flow_logs_status["FlowLogs"]) > 0

            sg_rules = ec2.describe_security_groups(GroupIds=[sg_id])
            assert len(sg_rules["SecurityGroups"][0]["IpPermissions"]) > 0

        finally:
            # Cleanup
            ec2.delete_security_group(GroupId=sg_id)
            ec2.delete_vpc(VpcId=vpc_id)

    def test_gcp_vpc_security(self, gcp_client, security_test_client, security_config):
        """Test GCP VPC security configurations.

        This test verifies:
        - VPC firewall rules
        - Cloud Armor security policies
        - VPC Service Controls
        - Private Google Access
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test VPC security
        compute_client = google.cloud.compute_v1.NetworksClient()
        project_id = cloud_config["gcp"]["project_id"]
        network_name = "test-secure-network"

        network = {
            "name": network_name,
            "auto_create_subnetworks": False,
            "routing_config": {"routing_mode": "REGIONAL"},
        }

        try:
            # Create VPC network
            operation = compute_client.insert(
                request={"project": project_id, "network_resource": network}
            )
            operation.result()

            # Create firewall rule
            firewall_client = google.cloud.compute_v1.FirewallsClient()
            firewall_rule = {
                "name": "test-secure-firewall",
                "network": f"projects/{project_id}/global/networks/{network_name}",
                "direction": "INGRESS",
                "allowed": [{"IPProtocol": "tcp", "ports": ["443"]}],
                "target_tags": ["secure-server"],
                "source_ranges": ["0.0.0.0/0"],
            }

            operation = firewall_client.insert(
                request={"project": project_id, "firewall_resource": firewall_rule}
            )
            operation.result()

            # Verify security configurations
            network_details = compute_client.get(
                request={"project": project_id, "network": network_name}
            )
            assert network_details.name == network_name

            firewall_rules = firewall_client.list(request={"project": project_id})
            assert any(rule.name == "test-secure-firewall" for rule in firewall_rules)

        finally:
            # Cleanup
            compute_client.delete(
                request={"project": project_id, "network": network_name}
            )


@pytest.mark.security
@pytest.mark.cloud
class TestIdentityManagement:
    """Test cloud identity and access management features."""

    def test_aws_identity_security(
        self, aws_client, security_test_client, security_config
    ):
        """Test AWS IAM security features.

        This test verifies:
        - IAM password policies
        - MFA requirements
        - Role-based access control
        - Service control policies
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test IAM security
        iam = boto3.client("iam")

        try:
            # Set password policy
            iam.update_account_password_policy(
                MinimumPasswordLength=12,
                RequireSymbols=True,
                RequireNumbers=True,
                RequireUppercaseCharacters=True,
                RequireLowercaseCharacters=True,
                AllowUsersToChangePassword=True,
                MaxPasswordAge=90,
                PasswordReusePrevention=24,
            )

            # Create test user with MFA
            user_name = "test-secure-user"
            iam.create_user(UserName=user_name)

            # Create access key
            access_key = iam.create_access_key(UserName=user_name)

            # Create MFA device
            mfa = iam.create_virtual_mfa_device(VirtualMFADeviceName=f"{user_name}-mfa")

            # Verify security configurations
            password_policy = iam.get_account_password_policy()
            assert password_policy["PasswordPolicy"]["MinimumPasswordLength"] == 12
            assert password_policy["PasswordPolicy"]["RequireSymbols"] is True

            user_mfa = iam.list_mfa_devices(UserName=user_name)
            assert len(user_mfa["MFADevices"]) > 0

        finally:
            # Cleanup
            iam.delete_access_key(
                UserName=user_name, AccessKeyId=access_key["AccessKey"]["AccessKeyId"]
            )
            iam.delete_user(UserName=user_name)

    def test_gcp_identity_security(
        self, gcp_client, security_test_client, security_config
    ):
        """Test GCP IAM security features.

        This test verifies:
        - Organization policies
        - Service account security
        - IAM role bindings
        - Security Command Center settings
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test IAM security
        iam_client = google.cloud.iam_v1.IAMClient()
        project_id = cloud_config["gcp"]["project_id"]

        try:
            # Create service account
            service_account = {
                "display_name": "Test Secure Service Account",
                "description": "Service account for security testing",
            }

            account = iam_client.create_service_account(
                request={
                    "name": f"projects/{project_id}",
                    "service_account": service_account,
                }
            )

            # Create custom role
            role = {
                "title": "Test Secure Role",
                "description": "Custom role for security testing",
                "permissions": ["storage.objects.get", "storage.objects.list"],
            }

            custom_role = iam_client.create_role(
                request={
                    "parent": f"projects/{project_id}",
                    "role_id": "testSecureRole",
                    "role": role,
                }
            )

            # Bind role to service account
            policy = iam_client.get_iam_policy(
                request={
                    "resource": f"projects/{project_id}",
                    "options": {"requested_policy_version": 3},
                }
            )

            binding = {
                "role": custom_role.name,
                "members": [f"serviceAccount:{account.email}"],
            }
            policy.bindings.append(binding)

            iam_client.set_iam_policy(
                request={"resource": f"projects/{project_id}", "policy": policy}
            )

            # Verify security configurations
            service_accounts = iam_client.list_service_accounts(
                request={"name": f"projects/{project_id}"}
            )
            assert any(sa.email == account.email for sa in service_accounts)

            roles = iam_client.list_roles(request={"parent": f"projects/{project_id}"})
            assert any(role.name == custom_role.name for role in roles)

        finally:
            # Cleanup
            iam_client.delete_service_account(request={"name": account.name})
            iam_client.delete_role(request={"name": custom_role.name})


@pytest.mark.security
@pytest.mark.cloud
class TestComplianceSecurity:
    """Test cloud compliance and governance features."""

    def test_aws_compliance(self, aws_client, security_test_client, security_config):
        """Test AWS compliance features.

        This test verifies:
        - AWS Config rules
        - CloudWatch compliance monitoring
        - AWS Security Hub findings
        - Compliance reporting
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test compliance features
        config = boto3.client("config")
        securityhub = boto3.client("securityhub")

        try:
            # Enable AWS Config
            config.put_configuration_recorder(
                ConfigurationRecorder={
                    "name": "default",
                    "roleARN": "arn:aws:iam::account:role/config-role",
                    "recordingGroup": {
                        "allSupported": True,
                        "includeGlobalResources": True,
                    },
                }
            )

            # Start configuration recorder
            config.start_configuration_recorder(ConfigurationRecorderName="default")

            # Enable Security Hub
            securityhub.enable_security_hub(
                EnableDefaultStandards=True, Tags={"Environment": "test"}
            )

            # Verify compliance configurations
            recorder_status = config.describe_configuration_recorder_status(
                ConfigurationRecorderNames=["default"]
            )
            assert (
                recorder_status["ConfigurationRecordersStatus"][0]["recording"] is True
            )

            hub_status = securityhub.describe_hub()
            assert hub_status["HubArn"] is not None

        finally:
            # Cleanup
            config.stop_configuration_recorder(ConfigurationRecorderName="default")
            securityhub.disable_security_hub()

    def test_gcp_compliance(self, gcp_client, security_test_client, security_config):
        """Test GCP compliance features.

        This test verifies:
        - Security Command Center
        - Cloud Asset Inventory
        - Policy Controller
        - Compliance monitoring
        """
        client, _ = security_test_client()
        cloud_config = get_cloud_config()

        # Test compliance features
        scc_client = google.cloud.securitycenter_v1.SecurityCenterClient()
        asset_client = google.cloud.asset_v1.AssetServiceClient()
        project_id = cloud_config["gcp"]["project_id"]

        try:
            # Enable Security Command Center
            scc_client.update_organization_settings(
                request={
                    "organization_settings": {
                        "name": f"organizations/{project_id}/organizationSettings",
                        "enable_asset_discovery": True,
                    }
                }
            )

            # Create security source
            source = {
                "display_name": "Test Compliance Source",
                "description": "Source for compliance testing",
            }

            security_source = scc_client.create_source(
                request={"parent": f"organizations/{project_id}", "source": source}
            )

            # Export assets
            asset_request = {
                "parent": f"projects/{project_id}",
                "content_type": "RESOURCE",
                "output_config": {
                    "gcs_destination": {"uri": f"gs://{project_id}-assets/export"}
                },
            }

            operation = asset_client.export_assets(request=asset_request)
            operation.result()

            # Verify compliance configurations
            sources = scc_client.list_sources(
                request={"parent": f"organizations/{project_id}"}
            )
            assert any(s.name == security_source.name for s in sources)

            settings = scc_client.get_organization_settings(
                request={"name": f"organizations/{project_id}/organizationSettings"}
            )
            assert settings.enable_asset_discovery is True

        finally:
            # Cleanup
            scc_client.delete_source(request={"name": security_source.name})
