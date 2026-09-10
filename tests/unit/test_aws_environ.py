"""Tests for fogies.tools.aws_environ."""

import os
from pathlib import Path

import pytest

from fogies.tools.aws_environ import (
    AwsProfile,
    aws_environ_from_profile,
    aws_environ_from_toml,
)


def test_aws_environ_from_profile_sets_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """aws_environ_from_profile sets variables from an AwsProfile using environ."""

    # Start from a clean environment for these variables within this test.
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    profile = AwsProfile(
        name="test",
        aws_access_key_id="value-aws-access-key-id",
        aws_secret_access_key="value-aws-secret-access-key",
    )
    other_profile = AwsProfile(
        name="test-other",
        aws_access_key_id="other-value-aws-access-key-id",
        aws_secret_access_key="other-value-aws-secret-access-key",
    )

    with aws_environ_from_profile(profile=profile) as env:
        assert env.profile == "test"
        assert env.aws_access_key_id == "value-aws-access-key-id"
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "value-aws-access-key-id"
        assert os.environ.get("AWS_SECRET_ACCESS_KEY") == "value-aws-secret-access-key"

    with aws_environ_from_profile(profile=other_profile) as env:
        assert env.profile == "test-other"
        assert env.aws_access_key_id == "other-value-aws-access-key-id"
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "other-value-aws-access-key-id"
        assert (
            os.environ.get("AWS_SECRET_ACCESS_KEY")
            == "other-value-aws-secret-access-key"
        )

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ


def test_aws_environ_from_toml_reads_selected_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """aws_environ_from_toml loads the named profile's credentials from the file.

    Env-var set/restore mechanics are covered by
    test_aws_environ_from_profile_sets_variables; aws_environ_from_toml
    delegates to aws_environ_from_profile for that. This test only covers
    what's specific to aws_environ_from_toml: reading the right profile out
    of a multi-profile file.
    """
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    profiles_path = tmp_path / "test_aws_environ.toml"
    config_text = "\n".join(
        [
            "[test]",
            'aws_access_key_id = "value-aws-access-key-id"',
            'aws_secret_access_key = "value-aws-secret-access-key"',
            "",
            "[test-other]",
            'aws_access_key_id = "other-value-aws-access-key-id"',
            'aws_secret_access_key = "other-value-aws-secret-access-key"',
            "",
        ]
    )
    _ = profiles_path.write_text(config_text, encoding="utf-8")

    with aws_environ_from_toml(
        profiles_path=profiles_path, profile_name="test-other"
    ) as env:
        assert env.profile == "test-other"
        assert env.aws_access_key_id == "other-value-aws-access-key-id"
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "other-value-aws-access-key-id"
        assert (
            os.environ.get("AWS_SECRET_ACCESS_KEY")
            == "other-value-aws-secret-access-key"
        )

    assert "AWS_ACCESS_KEY_ID" not in os.environ


def test_aws_environ_from_toml_raises_for_missing_file(tmp_path: Path) -> None:
    """aws_environ_from_toml raises FileNotFoundError when profiles file does not exist."""
    profiles_path = tmp_path / "missing.toml"

    with pytest.raises(FileNotFoundError):
        with aws_environ_from_toml(profiles_path=profiles_path, profile_name="test"):
            pass


def test_aws_environ_from_toml_raises_for_toml_extension(tmp_path: Path) -> None:
    """aws_environ_from_toml raises ValueError when profiles path lacks .toml extension."""
    profiles_path = tmp_path / "aws.env"

    with pytest.raises(ValueError, match=r"must have \.toml extension"):
        with aws_environ_from_toml(profiles_path=profiles_path, profile_name="test"):
            pass
