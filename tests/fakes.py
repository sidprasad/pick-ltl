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
        return self.payload

