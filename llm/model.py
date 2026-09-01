from functools import lru_cache
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from config import LLM_MODEL, LLM_TEMPERATURE

load_dotenv()


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    return ChatGroq(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
    )
