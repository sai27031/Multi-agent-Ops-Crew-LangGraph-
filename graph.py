import json
import time
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from nodes.coder import generate_code
from nodes.executor import run_code
from nodes.debugger import debug_code
from config import MAX_RETRIES, LOG_FILE


class CrewState(TypedDict):
    task_description: str
    current_code: str
    execution_result: Optional[dict]
    attempt: int
    status: str  # "in_progress" | "success" | "failed"
    history: list  # record of every attempt, for logging


def coder_node(state: CrewState) -> CrewState:
    if state["attempt"] == 0:
        code = generate_code(state["task_description"])
    else:
        last = state["history"][-1]
        code = debug_code(
            state["task_description"],
            last["code"],
            last["error"],
        )
    return {**state, "current_code": code}


def executor_node(state: CrewState) -> CrewState:
    result = run_code(state["current_code"])
    attempt_record = {
        "attempt": state["attempt"] + 1,
        "code": state["current_code"],
        "success": result["success"],
        "error": result["stderr"] if not result["success"] else None,
    }
    new_history = state["history"] + [attempt_record]

    if result["success"]:
        status = "success"
    elif state["attempt"] + 1 >= MAX_RETRIES:
        status = "failed"
    else:
        status = "in_progress"

    return {
        **state,
        "execution_result": result,
        "attempt": state["attempt"] + 1,
        "status": status,
        "history": new_history,
    }


def route_after_execution(state: CrewState) -> str:
    if state["status"] == "success":
        return "done"
    elif state["status"] == "failed":
        return "done"
    else:
        return "retry"


def log_run(state: CrewState):
    log_entry = {
        "task": state["task_description"],
        "final_status": state["status"],
        "total_attempts": state["attempt"],
        "history": state["history"],
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def build_graph():
    graph = StateGraph(CrewState)

    graph.add_node("coder", coder_node)
    graph.add_node("executor", executor_node)

    graph.set_entry_point("coder")
    graph.add_edge("coder", "executor")
    graph.add_conditional_edges(
        "executor",
        route_after_execution,
        {
            "retry": "coder",
            "done": END,
        },
    )

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    task = "Write a function called process_data that reads a CSV file called 'data.csv', calculates the sum of the 'amount' column, and prints the total. Assume the file exists in the current directory."
    initial_state: CrewState = {
        "task_description": task,
        "current_code": "",
        "execution_result": None,
        "attempt": 0,
        "status": "in_progress",
        "history": [],
    }

    final_state = app.invoke(initial_state)

    log_run(final_state)

    print(f"\n--- Final status: {final_state['status']} ---")
    print(f"Total attempts: {final_state['attempt']}")
    print("\n--- Final code ---")
    print(final_state["current_code"])

    if final_state["status"] == "failed":
        print("\n--- Last error (unresolved) ---")
        print(final_state["history"][-1]["error"])