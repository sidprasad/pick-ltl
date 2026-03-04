from pick_ltl.llm.base import LLMProvider, ProviderConfig


class DummyProvider(LLMProvider):
    def __init__(self):
        super().__init__(ProviderConfig(kind="dummy", base_url="http://dummy"))

    def list_models(self) -> list[str]:
        return []

    def test_connection(self) -> dict:
        return {"ok": True}

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError


def test_parse_json_extracts_object_from_extra_text():
    provider = DummyProvider()

    payload = provider.parse_json('Here is the result:\n{"formula":"G(r)","explanation":"seed","atoms":[],"warnings":[]}\nThanks!')

    assert payload["formula"] == "G(r)"
