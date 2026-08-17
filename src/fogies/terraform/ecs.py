"""Pydantic models for Terraform ECS module variables and output."""

from pydantic import BaseModel


class EcsVars(BaseModel):
    region: str
    name: str
    vpc_id: str
    subnet_ids: list[str]
    security_group_ids: list[str]
    listener_https_arn: str
    listener_rule_priority: int
    log_group_name: str | None
    image: str
    container_port: int
    cpu: int
    memory: int
    desired_count: int
    deregistration_delay: int = 300
    stop_timeout: int = 30
    tags: dict[str, str] = {}


class EcsOutput(BaseModel):
    cluster_arn: str
    service_name: str
    task_definition_arn: str
    target_group_arn: str
