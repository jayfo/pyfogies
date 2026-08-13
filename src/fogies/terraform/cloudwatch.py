"""Pydantic models for Terraform CloudWatch module variables and output."""

from pydantic import BaseModel


class CloudwatchVars(BaseModel):
    name: str
    retention_in_days: int = 0
    tags: dict[str, str] = {}


class CloudwatchOutput(BaseModel):
    log_group_name: str
    log_group_arn: str
