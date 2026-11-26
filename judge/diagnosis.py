from judge.errors import JudgeConfigError, JudgeError


class Diagnoser:
    """Asks the judge to explain failed test cases. Make one per suite run."""

    def __init__(self, ask):
        self._ask = ask
        self._off = False
        self._unavailable = None

    def diagnose(self, case, actual_output, reason):
        if self._off:
            return self._unavailable

        prompt = (
            "A test failed for an AI agent. Diagnose why and suggest a fix.\n\n"
            f"Input: {case['input']}\n"
            f"Expected: {case['expected_output']}\n"
            f"Actual: {actual_output}\n"
            f"Reason: {reason}"
        )
        try:
            return self._ask(prompt).text
        except JudgeConfigError:
            # No judge set up. Diagnosis is optional, so stay quiet and stop asking.
            self._off = True
            self._unavailable = None
            return None
        except JudgeError as err:
            # The judge broke. Say so, and skip it for the rest of this run.
            self._off = True
            self._unavailable = f"[Diagnosis unavailable: {err}]"
            return self._unavailable