# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Mock Agent Framework for testing Round Table

This module provides a deterministic mock agent framework for testing
agent interactions without requiring actual AI agent implementations.
"""

from .base import MockAgent
from .behaviors import (
    EchoBehavior,
    CalculatorBehavior,
    ResearcherBehavior,
    DeveloperBehavior,
    create_echo_agent,
    create_calculator_agent,
    create_researcher_agent,
    create_developer_agent,
)
from .registry import AgentRegistry
from .scenarios import TestScenario

__all__ = [
    "MockAgent",
    "EchoBehavior",
    "CalculatorBehavior",
    "ResearcherBehavior",
    "DeveloperBehavior",
    "create_echo_agent",
    "create_calculator_agent",
    "create_researcher_agent",
    "create_developer_agent",
    "AgentRegistry",
    "TestScenario",
]
