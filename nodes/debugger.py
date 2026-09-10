from nodes.coder import generate_code


def debug_code(task_description: str, failed_code: str, error_output: str) -> str:
    """
    The Debugger node. Takes the task, the code that failed, and the real
    error from the Executor, and asks the Coder to produce a fixed version.

    This reuses generate_code()'s error_context path rather than duplicating
    prompt logic — the Coder and Debugger are the same underlying call,
    just invoked differently depending on whether there's a prior failure.
    """
    error_context = f"""The following code was generated for this task:

{failed_code}

Running it produced this error:
{error_output}"""

    fixed_code = generate_code(task_description, error_context=error_context)
    return fixed_code


if __name__ == "__main__":
    task = "Write a function that divides two numbers and prints the result, then call it with 10 and 0."
    broken_code = """def divide(a, b):
    return a / b

print(divide(10, 0))"""
    error = "ZeroDivisionError: division by zero"

    fixed = debug_code(task, broken_code, error)
    print("--- Fixed code ---")
    print(fixed)