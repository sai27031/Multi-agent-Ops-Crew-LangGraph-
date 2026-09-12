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

REPORT_WRITER_PROMPT = """You are a technical report writer.

Given the details of a completed automated coding run, write a short,
clear summary suitable for inclusion in a project report.

Rules:
- 3-5 sentences, plain prose, no markdown headers or bullet points.
- State what the task was, how many attempts it took, and whether it
  ultimately succeeded or failed.
- If there were failures, describe the fix ONLY in terms of what changed
  in the code between the failed attempt and the successful one — do not
  describe changes to the environment, files, or external state unless
  the code history explicitly shows that. If you are not certain what
  changed, say "the code was modified to handle this case" rather than
  guessing specifics.
- Do not invent details not present in the run history.
"""


def write_report(task_description: str, final_status: str, attempts: int, history: list) -> str:
    """
    The Report Writer node. Takes the completed run's data and produces
    a short human-readable summary. This is the final step after the
    Coder-Executor-Debugger loop ends, not part of the retry loop itself.
    """
    history_summary = ""
    for entry in history:
        outcome = "succeeded" if entry["success"] else f"failed with: {entry['error']}"
        history_summary += f"Attempt {entry['attempt']} code:\n{entry['code']}\nOutcome: {outcome}\n\n"

    user_prompt = (
        "Task: " + task_description + "\n"
        "Final status: " + final_status + "\n"
        "Total attempts: " + str(attempts) + "\n\n"
        "Attempt history:\n" + history_summary
    )

    response = llm.invoke([
        ("system", REPORT_WRITER_PROMPT),
        ("human", user_prompt),
    ])
    return response.content.strip()


if __name__ == "__main__":
    task = "Write a function called process_data that reads a CSV file called 'data.csv', calculates the sum of the 'amount' column, and prints the total."
    history = [
    {
        "attempt": 1,
        "success": False,
        "error": "FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'",
        "code": "import csv\n\ndef process_data():\n    with open('data.csv') as f:\n        pass",
    },
    {
        "attempt": 2,
        "success": True,
        "error": None,
        "code": "import csv\nimport os\n\ndef process_data():\n    if not os.path.isfile('data.csv'):\n        print(0.0)\n        return\n    with open('data.csv') as f:\n        pass",
    },
]

    report = write_report(task, "success", 2, history)
    print("--- Generated report ---")
    print(report)