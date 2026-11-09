"""Model call: prompt from a file → JSON reply → validation → one retry on error.

Also tracks tokens, run cost, and mock mode (replies from tests/fixtures).
"""
import json
import re
from pathlib import Path
from typing import Callable

MODEL = "claude-sonnet-5-5"
PRICE_IN = 2.0    # $ per 1M input tokens
PRICE_OUT = 10.0  # $ per 1M output tokens
MAX_TOKENS = 8000

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


class LLMError(Exception):
    """The model gave no usable reply (or there is no mock fixture)."""


def render_prompt(name: str, variables: dict) -> str:
    """Reads prompts/<name>.md and fills in {{variables}}.

    Not str.format: the prompts contain the curly braces of JSON schemas.
    """
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    for key, value in variables.items():
        if not isinstance(value, str):
            value = json.dumps(value, indent=2, ensure_ascii=False)
        text = text.replace("{{" + key + "}}", value)
    missing = PLACEHOLDER_RE.findall(text)
    if missing:
        raise LLMError(f"prompt {name}.md: no value for {', '.join(missing)}")
    return text


def parse_json(text: str) -> dict:
    """Strips a ```json ... ``` wrapper (the model sometimes adds one, with text around it) and parses the object."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    data = json.loads(cleaned)  # json.JSONDecodeError is a subclass of ValueError
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object at the top level")
    return data


class LLM:
    def __init__(self, model: str = MODEL, mock: bool = False, client=None):
        self.model = model
        self.mock = mock
        self._client = client
        self.usage: list[dict] = []

    @property
    def client(self):
        # The client is created lazily: mock mode needs neither a key nor the network.
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def ask_json(self, step: str, prompt_name: str, variables: dict,
                 validate: Callable[[dict], None], fixture: str | None = None) -> dict:
        """Returns a validated dict. validate raises ValueError explaining what is wrong."""
        if self.mock:
            return self._from_fixture(step, fixture or step, validate)

        messages = [{"role": "user", "content": render_prompt(prompt_name, variables)}]
        raw, truncated = self._call(step, messages)
        try:
            if truncated:
                raise ValueError("the reply was cut off at max_tokens; reply with shorter, complete JSON")
            return self._check(raw, validate)
        except ValueError as first_error:
            # One retry: show the model its reply and the error text.
            messages += [
                {"role": "assistant", "content": raw or "(empty)"},
                {"role": "user", "content": f"Your previous reply was invalid: {first_error}. "
                                            "Reply with the corrected JSON only."},
            ]
            raw, _ = self._call(step, messages)
            try:
                return self._check(raw, validate)
            except ValueError as second_error:
                raise LLMError(f"step {step}: invalid model reply after retry: {second_error}") from None

    def _call(self, step: str, messages: list[dict]) -> tuple[str, bool]:
        """Returns (text, whether it was cut off at max_tokens)."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            output_config={"effort": "low"},  # short texts: speed matters more than depth
            messages=messages,
        )
        self.usage.append({"step": step, "input_tokens": response.usage.input_tokens,
                           "output_tokens": response.usage.output_tokens})
        if response.stop_reason == "refusal":
            raise LLMError(f"step {step}: the model refused to answer")
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, response.stop_reason == "max_tokens"

    @staticmethod
    def _check(raw: str, validate: Callable[[dict], None]) -> dict:
        data = parse_json(raw)
        validate(data)
        return data

    def _from_fixture(self, step: str, name: str, validate: Callable[[dict], None]) -> dict:
        path = FIXTURES_DIR / f"{name}.json"
        if not path.exists():
            raise LLMError(f"no mock fixture {name}.json")
        self.usage.append({"step": step, "input_tokens": 0, "output_tokens": 0})
        try:
            return self._check(path.read_text(encoding="utf-8"), validate)
        except ValueError as e:
            raise LLMError(f"mock fixture {name}.json is invalid: {e}") from None

    def cost(self) -> float:
        tokens_in = sum(u["input_tokens"] for u in self.usage)
        tokens_out = sum(u["output_tokens"] for u in self.usage)
        return (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1_000_000
