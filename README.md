# Multi-agent Ops Crew (LangGraph)

A multi-agent coding system that turns a raw, informally-written task description into working, tested Python code — reading the spec, generating code, actually running it in a sandbox, and fixing it based on real runtime errors when it fails.

Built with LangGraph, Groq (`openai/gpt-oss-120b`), and Python.

## Why this exists

Most "AI coding agent" demos generate code and stop — they never check whether it actually runs. This project's core idea is that generating code is the easy part; **verifying it and recovering from real failures is the hard part**, and that's what most tutorial-level agent projects skip.

## Architecture

The system is a graph of five agents, each with one job:

1. **Spec Reader** — takes a raw, informal task description (which may be vague or rambling) and extracts a single, concrete, buildable task.
2. **Coder** — generates Python code for the task.
3. **Executor** — actually runs the generated code in a sandboxed subprocess (isolated temp directory, CPU-time limit, wall-clock timeout) and captures the real stdout/stderr/exit code. No guessing — this is a real execution, not the LLM predicting what might happen.
4. **Debugger** — if execution fails, takes the actual error output and produces a fix. This is not the same as regenerating from scratch: it's given the exact traceback and asked to resolve that specific failure.
5. **Report Writer** — once the loop ends (success or max retries reached), writes a plain-language summary of what happened across all attempts.

**Control flow:**

```
Spec Reader → Coder → Executor → (success) → Report Writer → END
                  ↑         |
                  |     (failure, retries remaining)
                  |         ↓
              Debugger ←────┘
```

A hard retry cap (`MAX_RETRIES` in `config.py`) prevents infinite loops. If the cap is hit without success, the system reports failure honestly rather than returning broken code with false confidence.

Every run is logged to `run_log.jsonl` — task, every attempt's code and outcome, final status, and the generated report. This is what makes the claims below verifiable rather than anecdotal.

## What I actually found while building this

The Executor's sandbox runs code in a fresh, empty temporary directory on every attempt. The first real multi-step failure I hit wasn't a code bug — it was a **task/environment mismatch**: I gave it a task that assumed a pre-existing `data.csv` file, and the Debugger correctly diagnosed a `FileNotFoundError` and tried several path-resolution strategies (relative path, then `os.path.dirname(__file__)`) across multiple attempts — all of which failed, because no path fix can conjure a file the sandbox never provides.

This hit `MAX_RETRIES` and reported failure — correctly. The fix wasn't a code change at all; it was adding fixture support to the Executor so it can write expected input files into the sandbox before running generated code. This is documented in `run_log.jsonl` as a real failed run, not scrubbed from history.

**Current limitation, stated plainly:** fixture files are currently hardcoded (a fixed `data.csv` with fixed sample data) rather than dynamically generated based on what a task actually needs. A more complete version would have the Spec Reader detect required inputs and generate matching fixtures automatically. This is a known scope boundary, not an oversight.

## Platform note

Memory limiting (`RLIMIT_AS`) in the sandbox is skipped on macOS — it conflicts with how macOS handles virtual address space on fork/exec and causes `setrlimit` to fail before the child process starts. CPU-time limiting and the subprocess timeout serve as the safety net on macOS; full memory capping is available on Linux.

## Setup

```bash
git clone https://github.com/sai27031/Multi-agent-Ops-Crew-LangGraph-
cd Multi-agent-Ops-Crew-LangGraph-
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

## Running it

Edit the `raw_spec` string in `graph.py`'s `if __name__ == "__main__":` block to your task, then:

```bash
python -m graph
```

Output includes the final status, the working code (or the last failed attempt if unresolved), and a plain-language report. Every run appends a full record to `run_log.jsonl`.

## Stack

- **LangGraph** — agent orchestration and conditional retry routing
- **Groq** (`openai/gpt-oss-120b`) — code generation, debugging, spec extraction, and report writing
- **Python subprocess + resource limits** — sandboxed code execution

## Tested cases

- CSV aggregation task with a missing input file (failed at `MAX_RETRIES`, root-caused above)
- Same task with fixture support added (succeeded on first attempt)
- Non-file-I/O task (palindrome check with punctuation/case normalization) — succeeded on first attempt

This is a small sample, not a benchmark — reported as such rather than overstated.
