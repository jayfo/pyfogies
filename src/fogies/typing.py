"""Typing helpers for cleanly annotating loosely-typed third-party APIs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_s3.client import S3Client


def boto_client_ec2(*, region: str) -> EC2Client:
    """Obtain a boto3 EC2 client for region."""
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "ec2", region_name=region
    )


def boto_client_ecs(*, region: str) -> ECSClient:
    """Obtain a boto3 ECS client for region."""
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "ecs", region_name=region
    )


def boto_client_logs(*, region: str) -> CloudWatchLogsClient:
    """Obtain a boto3 CloudWatch Logs client for region."""
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "logs", region_name=region
    )


def boto_client_s3(*, region: str) -> S3Client:
    """Obtain a boto3 S3 client for region."""
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3", region_name=region
    )
