import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from config import GROQ_MODEL

load_dotenv()

llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SPEC_READER_PROMPT = """You are a requirements extractor.

Given a raw spec or task description (which may be messy, informal, or
contain irrelevant context), extract a single clear, concrete coding task.

Rules:
- Output ONLY the extracted task description as plain text.
- No preamble, no explanation, no markdown formatting.
- The output should be specific enough that a developer could start coding
  immediately from it — include function names, expected inputs, and
  expected behavior if the spec mentions them.
- If the spec describes multiple tasks, pick the single most concrete,
  buildable one and state only that.
"""


def extract_task(raw_spec: str) -> str:
    """
    The Spec Reader node. Takes raw spec text (from a file, a pasted
    paragraph, etc.) and returns a clean, concrete task description
    that the Coder node can act on directly.
    """
    response = llm.invoke([
        ("system", SPEC_READER_PROMPT),
        ("human", raw_spec),
    ])
    return response.content.strip()


def read_spec_file(file_path: str) -> str:
    """
    Reads a spec from a text file on disk.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    raw_spec = """
    So for this part of the project I need something that can take in a
    list of temperatures in Celsius and I guess convert all of them to
    Fahrenheit, and also tell me which one was the hottest day. Probably
    should print both things out. Doesn't need to be fancy.
    """

    task = extract_task(raw_spec)
    print("--- Extracted task ---")
    print(task)