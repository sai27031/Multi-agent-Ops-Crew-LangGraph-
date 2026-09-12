import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from nodes.spec_reader import extract_task
from nodes.coder import generate_code
from nodes.executor import run_code
from nodes.debugger import debug_code
from nodes.report_writer import write_report
from config import MAX_RETRIES, LOG_FILE


class CrewState(TypedDict):
    raw_spec: str
    task_description: str
    current_code: str
    execution_result: Optional[dict]
    attempt: int
    status: str
    history: list
    report: str


def spec_reader_node(state: CrewState) -> CrewState:
    task = extract_task(state["raw_spec"])
    return {**state, "task_description": task}


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
    fixtures = {"data.csv": "amount\n10.5\n20.0\n5.25\n"}
    result = run_code(state["current_code"], fixture_files=fixtures)
    ...

    
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


def report_writer_node(state: CrewState) -> CrewState:
    report = write_report(
        state["task_description"],
        state["status"],
        state["attempt"],
        state["history"],
    )
    return {**state, "report": report}


def route_after_execution(state: CrewState) -> str:
    if state["status"] in ("success", "failed"):
        return "report"
    return "retry"


def log_run(state: CrewState):
    log_entry = {
        "task": state["task_description"],
        "final_status": state["status"],
        "total_attempts": state["attempt"],
        "history": state["history"],
        "report": state["report"],
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def build_graph():
    graph = StateGraph(CrewState)

    graph.add_node("spec_reader", spec_reader_node)
    graph.add_node("coder", coder_node)
    graph.add_node("executor", executor_node)
    graph.add_node("report_writer", report_writer_node)

    graph.set_entry_point("spec_reader")
    graph.add_edge("spec_reader", "coder")
    graph.add_edge("coder", "executor")
    graph.add_conditional_edges(
        "executor",
        route_after_execution,
        {
            "retry": "coder",
            "report": "report_writer",
        },
    )
    graph.add_edge("report_writer", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    raw_spec = """
    So for this part I need something that reads a CSV file called
    data.csv and adds up everything in the 'amount' column, then
    prints the total. Assume the file exists in the current directory.
    """

    initial_state: CrewState = {
        "raw_spec": raw_spec,
        "task_description": "",
        "current_code": "",
        "execution_result": None,
        "attempt": 0,
        "status": "in_progress",
        "history": [],
        "report": "",
    }

    final_state = app.invoke(initial_state)

    log_run(final_state)

    print(f"\n--- Final status: {final_state['status']} ---")
    print(f"Total attempts: {final_state['attempt']}")
    print("\n--- Final code ---")
    print(final_state["current_code"])
    print("\n--- Report ---")
    print(final_state["report"])