import os
os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
from advoi.routing.agent_supervisor import DEFAULT_AGENT_IDS
from advoi.routing.agents import AGENTS

def test_supervisor_covers_all_specialists():
    assert set(DEFAULT_AGENT_IDS) == set(AGENTS.keys())
    assert len(DEFAULT_AGENT_IDS) == 6