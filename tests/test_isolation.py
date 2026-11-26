import os

import main  # importing main loads .env, which is exactly the situation we guard against


def test_real_judge_settings_are_not_visible_to_tests():
    for name in ("JUDGE_API_KEY", "GEMINI_API_KEY"):
        assert name not in os.environ