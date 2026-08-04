import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import get_settings
from app.models import AgentInvokeRequest, SpendingEvent
from app.service import EconomicSpendingService


class EconomicAgentTests(unittest.TestCase):
    def setUp(self):
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()

    def test_agent_returns_findings_and_proposed_actions(self):
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict(
            "os.environ",
            {"ECONOMIC_SPENDING_DATA_PATH": str(Path(tmp_dir) / "events.jsonl")},
            clear=False,
        ):
            get_settings.cache_clear()
            service = EconomicSpendingService()
            service.record_event(
                SpendingEvent(
                    user_id="moshe",
                    amount="6000",
                    category="tools",
                    description="large tools purchase",
                )
            )

            response = service.invoke_agent(AgentInvokeRequest(task="analyze", user_id="moshe"))

        self.assertIn("high_recent_spending", response.signals)
        self.assertTrue(response.findings)
        self.assertTrue(response.proposed_actions)
        self.assertTrue(response.requires_approval)


if __name__ == "__main__":
    unittest.main()
