import subprocess
import tempfile
import os
import resource
import sys

def limit_resources(cpu_seconds=5, memory_mb=256):
    """
    Runs inside the child process before the generated code executes.
    Caps CPU time everywhere. Memory capping via RLIMIT_AS is skipped on
    macOS — it conflicts with how macOS handles virtual address space on
    fork, and causes setrlimit to fail before the child process even
    starts. On macOS, the subprocess timeout is the safety net instead.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    if sys.platform != "darwin":
        memory_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))


def run_code(code: str, timeout_seconds: int = 10, fixture_files: dict = None) -> dict:
    """
    fixture_files: optional dict of {filename: content} to write into the
    sandbox directory before running, simulating pre-existing input files
    the task assumes are present.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = os.path.join(tmp_dir, "generated_code.py")

        if fixture_files:
            for filename, content in fixture_files.items():
                with open(os.path.join(tmp_dir, filename), "w") as f:
                    f.write(content)

        with open(script_path, "w") as f:
            f.write(code)
        # ... rest unchanged

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                preexec_fn=limit_resources,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "returncode": None,
            }


if __name__ == "__main__":
    working_code = """
print("hello from generated code")
x = 2 + 2
print(x)
"""

    broken_code = """
print("about to fail")
x = 1 / 0
"""

    infinite_loop_code = """
while True:
    pass
"""

    for label, code in [
        ("WORKING", working_code),
        ("BROKEN", broken_code),
        ("INFINITE LOOP", infinite_loop_code),
    ]:
        print(f"\n--- Testing: {label} ---")
        print(run_code(code, timeout_seconds=5))