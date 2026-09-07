import pytest
from brain.agent_brain import AgentBrain


def test_agent_brain_fast_conversation():
    brain = AgentBrain()
    reply = brain.process_message("Hi maapla eppadi irukka?")
    assert reply is not None
    assert len(reply) > 5


def test_agent_brain_status_query():
    brain = AgentBrain()
    reply = brain.process_message("Andha task status enna mapla?")
    assert reply is not None
    assert any(k in reply.lower() for k in ["status", "completed", "ledger", "task"])


def test_agent_brain_device_presentation():
    brain = AgentBrain()
    reply = brain.process_message("Open panni kaatu mapla screen-la")
    assert reply is not None
    assert "laptop" in reply or "Drive" in reply or "screen" in reply
