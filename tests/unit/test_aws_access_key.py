"""Integration tests for fogies.aws_access_key against real AWS."""

from collections.abc import Callable, Iterator

import pytest

import fogies.aws_access_key as aws_access_key
from fogies.tools.aws_environ import AwsEnviron, AwsProfile
from fogies.typing import boto_client_sts

# Prefix for all scratch users created by these tests; makes them easy to identify and clean up.
_TEST_USERNAME_PREFIX = "pyfogies-test-aws-access-key-"


def _delete_prefixed_users() -> None:
    """Delete all IAM users matching the test prefix, including their keys."""
    for user in aws_access_key.list_users():
        if user.username.startswith(_TEST_USERNAME_PREFIX):
            for key in (user.keys.current, user.keys.previous):
                if key is not None:
                    aws_access_key.delete_key(username=user.username, key_id=key.key_id, protected_key_ids=set())
            aws_access_key.delete_user(username=user.username, protected_usernames=set())


@pytest.fixture(scope="module")
def test_aws_environ_username(pyfogies_test_aws_environ: AwsEnviron) -> str:
    """Return the IAM username currently authenticated by the test session."""
    _ = pyfogies_test_aws_environ
    arn = boto_client_sts().get_caller_identity()["Arn"]
    return arn.split("/")[-1]


@pytest.fixture(scope="module")
def test_user_factory(pyfogies_test_aws_environ: AwsEnviron) -> Iterator[Callable[[], AwsProfile]]:
    """Yield a factory that creates a fresh IAM user (with initial key) on each call.

    All prefixed users are swept on setup and teardown.
    """
    _ = pyfogies_test_aws_environ
    _delete_prefixed_users()
    test_user_count = 0

    def factory() -> AwsProfile:
        nonlocal test_user_count
        test_user_count += 1
        username = "{}{}".format(_TEST_USERNAME_PREFIX, test_user_count)
        return aws_access_key.create_user(username=username)

    try:
        yield factory
    finally:
        _delete_prefixed_users()


def test_create_user_raises_if_exists(test_user_factory: Callable[[], AwsProfile]) -> None:
    """create_user raises ValueError if the user already exists."""
    test_profile = test_user_factory()
    with pytest.raises(ValueError, match="already exists"):
        aws_access_key.create_user(username=test_profile.name)


def test_create_user_creates_initial_key(test_user_factory: Callable[[], AwsProfile]) -> None:
    """create_user returns an AwsProfile with credentials and a current key."""
    test_profile = test_user_factory()
    assert test_profile.aws_access_key_id.startswith("AKIA")
    assert len(test_profile.aws_secret_access_key) > 0

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.current is not None
    assert keys.current.key_id == test_profile.aws_access_key_id
    assert keys.previous is None


def test_list_users_includes_new_user(test_user_factory: Callable[[], AwsProfile]) -> None:
    """list_users returns a newly created user."""
    test_profile = test_user_factory()
    users = aws_access_key.list_users()
    assert any(u.username == test_profile.name for u in users)


def test_rotate_key_creates_new_current(
    pyfogies_test_aws_environ: AwsEnviron,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """rotate_key creates a new current key; the original key becomes previous."""
    test_profile = test_user_factory()
    rotated = aws_access_key.rotate_key(username=test_profile.name, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})
    assert rotated.aws_access_key_id.startswith("AKIA")
    assert rotated.aws_access_key_id != test_profile.aws_access_key_id

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.current is not None
    assert keys.current.key_id == rotated.aws_access_key_id
    assert keys.previous is not None
    assert keys.previous.key_id == test_profile.aws_access_key_id


def test_rotate_key_deletes_existing_previous(
    pyfogies_test_aws_environ: AwsEnviron,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """A second rotate deletes the existing previous key; second_rotate is current, first_rotate is previous."""
    test_profile = test_user_factory()
    first_rotate = aws_access_key.rotate_key(username=test_profile.name, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.previous is not None
    assert keys.previous.key_id == test_profile.aws_access_key_id

    second_rotate = aws_access_key.rotate_key(username=test_profile.name, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})

    assert second_rotate.aws_access_key_id != first_rotate.aws_access_key_id
    assert second_rotate.aws_access_key_id != test_profile.aws_access_key_id

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.current is not None
    assert keys.current.key_id == second_rotate.aws_access_key_id
    assert keys.previous is not None
    assert keys.previous.key_id == first_rotate.aws_access_key_id


def test_delete_key_removes_key(
    pyfogies_test_aws_environ: AwsEnviron,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """delete_key removes the specified key."""
    test_profile = test_user_factory()
    # Rotate to produce a previous slot (the original key from create_user).
    aws_access_key.rotate_key(username=test_profile.name, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.previous is not None
    aws_access_key.delete_key(username=test_profile.name, key_id=keys.previous.key_id, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})

    keys = aws_access_key.get_keys(username=test_profile.name)
    assert keys.current is not None
    assert keys.previous is None


def test_delete_key_refuses_protected_key(
    pyfogies_test_aws_environ: AwsEnviron,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """delete_key raises ValueError when asked to delete a protected key."""
    test_profile = test_user_factory()
    protected = {test_profile.aws_access_key_id, pyfogies_test_aws_environ.aws_access_key_id}
    with pytest.raises(ValueError, match="protected key"):
        aws_access_key.delete_key(
            username=test_profile.name,
            key_id=test_profile.aws_access_key_id,
            protected_key_ids=protected,
        )


def test_delete_user_raises_if_has_keys(
    test_aws_environ_username: str,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """delete_user raises ValueError when the user still has keys."""
    test_profile = test_user_factory()
    with pytest.raises(ValueError, match="still has"):
        aws_access_key.delete_user(username=test_profile.name, protected_usernames={test_aws_environ_username})


def test_delete_user_raises_if_protected(
    pyfogies_test_aws_environ: AwsEnviron,
    test_aws_environ_username: str,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """delete_user raises ValueError when the username is protected."""
    test_profile = test_user_factory()
    aws_access_key.delete_key(username=test_profile.name, key_id=test_profile.aws_access_key_id, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})
    with pytest.raises(ValueError, match="protected user"):
        aws_access_key.delete_user(
            username=test_profile.name,
            protected_usernames={test_profile.name, test_aws_environ_username},
        )


def test_delete_user_succeeds_after_keys_removed(
    pyfogies_test_aws_environ: AwsEnviron,
    test_aws_environ_username: str,
    test_user_factory: Callable[[], AwsProfile],
) -> None:
    """delete_user succeeds once all keys are gone."""
    test_profile = test_user_factory()
    aws_access_key.delete_key(username=test_profile.name, key_id=test_profile.aws_access_key_id, protected_key_ids={pyfogies_test_aws_environ.aws_access_key_id})
    aws_access_key.delete_user(username=test_profile.name, protected_usernames={test_aws_environ_username})

    users = aws_access_key.list_users()
    assert not any(u.username == test_profile.name for u in users)
