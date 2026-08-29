"""IAM user and access key management, independent of invoke."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from fogies.tools.aws_environ import AwsProfile
from fogies.typing import boto_client_iam

if TYPE_CHECKING:
    from mypy_boto3_iam.type_defs import AccessKeyMetadataTypeDef


class _IamAccessKeyInfo(BaseModel):
    key_id: str
    status: str
    created: datetime.datetime | None
    last_used: datetime.datetime | None


class _IamAccessKeys(BaseModel):
    current: _IamAccessKeyInfo | None  # newest key
    previous: _IamAccessKeyInfo | None  # oldest key; only present when two keys exist


class _IamUserInfo(BaseModel):
    username: str
    keys: _IamAccessKeys


def get_keys(*, username: str) -> _IamAccessKeys:
    """Return the access keys for a user as current (newest) and previous (oldest)."""
    iam = boto_client_iam()
    raw_keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
    sorted_keys = sorted(
        raw_keys,
        key=lambda k: k.get("CreateDate") or datetime.datetime.min,
        reverse=True,
    )

    def _to_info(raw_key: AccessKeyMetadataTypeDef) -> _IamAccessKeyInfo:
        key_id = raw_key.get("AccessKeyId", "")
        last_used_response = iam.get_access_key_last_used(AccessKeyId=key_id)
        last_used = last_used_response["AccessKeyLastUsed"].get("LastUsedDate")
        return _IamAccessKeyInfo(
            key_id=key_id,
            status=raw_key.get("Status", ""),
            created=raw_key.get("CreateDate"),
            last_used=last_used,
        )

    return _IamAccessKeys(
        current=_to_info(sorted_keys[0]) if len(sorted_keys) >= 1 else None,
        previous=_to_info(sorted_keys[1]) if len(sorted_keys) >= 2 else None,
    )


def list_users() -> list[_IamUserInfo]:
    """List all IAM users (sorted by name) and their access keys."""
    iam = boto_client_iam()
    users = [
        _IamUserInfo(username=user["UserName"], keys=get_keys(username=user["UserName"]))
        for user in iam.list_users()["Users"]
    ]
    return sorted(users, key=lambda u: u.username)


def create_user(*, username: str) -> AwsProfile:
    """Create a new IAM user and an access key. Raises if the user already exists."""
    iam = boto_client_iam()
    try:
        _ = iam.get_user(UserName=username)
        raise ValueError("User '{}' already exists.".format(username))
    except iam.exceptions.NoSuchEntityException:
        pass

    _ = iam.create_user(UserName=username)
    key = iam.create_access_key(UserName=username)["AccessKey"]
    return AwsProfile(
        name=username,
        aws_access_key_id=key["AccessKeyId"],
        aws_secret_access_key=key["SecretAccessKey"],
    )


def rotate_key(*, username: str, protected_key_ids: set[str]) -> AwsProfile:
    """Create a new access key for a user, deleting the previous key first if one exists.

    Raises ValueError if the previous key is in protected_key_ids.
    """
    existing = get_keys(username=username)
    if existing.previous is not None:
        delete_key(
            username=username,
            key_id=existing.previous.key_id,
            protected_key_ids=protected_key_ids,
        )

    iam = boto_client_iam()
    key = iam.create_access_key(UserName=username)["AccessKey"]
    return AwsProfile(
        name=username,
        aws_access_key_id=key["AccessKeyId"],
        aws_secret_access_key=key["SecretAccessKey"],
    )


def delete_key(*, username: str, key_id: str, protected_key_ids: set[str]) -> None:
    """Delete a specific access key for the user.

    Raises ValueError if key_id is in protected_key_ids.
    """
    if key_id in protected_key_ids:
        raise ValueError("Refusing to delete protected key '{}'.".format(key_id))
    _ = boto_client_iam().delete_access_key(UserName=username, AccessKeyId=key_id)


def delete_user(*, username: str, protected_usernames: set[str]) -> None:
    """Delete an IAM user. Raises if the user still has access keys or is protected."""
    if username in protected_usernames:
        raise ValueError("Refusing to delete protected user '{}'.".format(username))
    iam = boto_client_iam()
    keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
    if keys:
        raise ValueError(
            "User '{}' still has {} access key(s). Delete them first.".format(username, len(keys))
        )
    _ = iam.delete_user(UserName=username)
