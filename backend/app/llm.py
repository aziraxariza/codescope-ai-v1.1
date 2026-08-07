"""
Unified LLM wrapper.
Set LLM_PROVIDER=ollama for local dev (free, no API key).
Set LLM_PROVIDER=groq  for cloud deployment (Groq free tier).
"""

import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "ollama")


def chat(system: str, user: str) -> str:
    """Send a system + user message and return the LLM response as a string."""

    if PROVIDER == "groq":
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
            max_tokens=1024,
        )
        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        return llm.invoke(messages).content

    else:
        # Ollama — runs locally, completely free, no API key needed
        from langchain_community.llms import Ollama

        llm = Ollama(
            model="llama3.2:3b",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )
        prompt = f"System: {system}\n\nUser: {user}\n\nAssistant:"
        return llm.invoke(prompt)
