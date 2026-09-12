import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

from config import GROQ_MODEL

llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

CODER_SYSTEM_PROMPT = """You are a Python code generator.

Rules:
- Output ONLY raw Python code. No explanations, no markdown code fences, no comments about what you're doing.
- The code must be complete and runnable as-is via `python script.py`.
- If the task requires printing a result, use print() so output is visible when the script runs.
"""


def generate_code(task_description: str, error_context: str = None) -> str:
    """
    The Coder node. Takes a task description and returns generated code.
    If error_context is provided (from a previous failed run), the model
    is asked to fix that specific error instead of writing from scratch.
    """
    if error_context:
        user_prompt = f"""Task: {task_description}

Your previous attempt failed with this error:
{error_context}

Fix the code so it runs successfully. Output ONLY the corrected code."""
    else:
        user_prompt = f"Task: {task_description}\n\nWrite Python code to accomplish this."

    response = llm.invoke([
        ("system", CODER_SYSTEM_PROMPT),
        ("human", user_prompt),
    ])

    code = response.content.strip()

    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return code


if __name__ == "__main__":
    task = "Write a function that calculates the factorial of a number, then call it with the number 5 and print the result."
    code = generate_code(task)
    print("--- Generated code ---")
    print(code)