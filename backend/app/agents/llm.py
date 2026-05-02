"""Shared LLM instance — created once, reused by all agents."""
import os
from langchain_fireworks import ChatFireworks

_llm = None


def get_llm() -> ChatFireworks:
    global _llm
    if _llm is None:
        _llm = ChatFireworks(
            model="accounts/fireworks/models/llama-v3p3-70b-instruct",
            api_key=os.environ.get("FIREWORKS_API_KEY", ""),
            temperature=0,
        )
    return _llm
