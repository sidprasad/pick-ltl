from pick_ltl.llm.base import LLMProvider, ProviderConfig


class FakeLLMProvider(LLMProvider):
    def __init__(self, payload, config=None):
        super().__init__(config or ProviderConfig(kind="fake", base_url="http://fake"))
        self.payload = payload
        self.calls = []

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def test_connection(self) -> dict:
        return {"ok": True, "models": self.list_models()}

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        if isinstance(self.payload, list):
            if not self.payload:
                raise AssertionError("FakeLLMProvider ran out of payloads.")
            next_payload = self.payload.pop(0)
            if callable(next_payload):
                return next_payload(system_prompt, user_prompt)
            return next_payload
        if callable(self.payload):
            return self.payload(system_prompt, user_prompt)
        return self.payload
