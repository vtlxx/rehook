"""Фейковий клієнт Anthropic для тестів: відповідає заздалегідь заданим текстом."""
import threading
from types import SimpleNamespace


class _Messages:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        with self.owner.lock:
            self.owner.calls.append(kwargs)
            if callable(self.owner.replies):
                text = self.owner.replies(kwargs)
            else:
                text = self.owner.replies.pop(0)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
            stop_reason=self.owner.stop_reasons.pop(0) if self.owner.stop_reasons else "end_turn",
        )


class FakeClient:
    """replies: список (видається по черзі) або функція kwargs -> текст (для паралельних викликів)."""

    def __init__(self, replies, stop_reasons=None):
        self.replies = replies
        self.stop_reasons = list(stop_reasons or [])
        self.calls = []
        self.lock = threading.Lock()
        self.messages = _Messages(self)


def prompt_of(kwargs) -> str:
    """Текст першого повідомлення користувача у виклику."""
    return kwargs["messages"][0]["content"]
