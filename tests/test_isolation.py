import os

import main  # importing main loads .env, which is exactly the situation we guard against


def test_real_judge_settings_are_not_visible_to_tests():
    visible = [name for name in ("JUDGE_API_KEY", "GEMINI_API_KEY") if name in os.environ]
    assert visible == []  # names only; never print the environment