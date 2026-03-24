from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    attempts: int
    elapsed_s: float


def run_with_retries(
    args: Sequence[str],
    *,
    timeout_s: float | None = None,
    retries: int = 2,
    initial_backoff_s: float = 1.0,
    backoff_mult: float = 2.0,
) -> RunResult:
    """
    Run a subprocess with timeout and retry/backoff.
    Retries on non-zero exit OR TimeoutExpired.
    """
    attempts = 0
    start = time.monotonic()
    backoff = initial_backoff_s
    last: subprocess.CompletedProcess[str] | None = None
    last_stderr = ""
    last_stdout = ""
    last_rc = 1

    for i in range(retries + 1):
        attempts = i + 1
        try:
            cp = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            last = cp
            last_rc = cp.returncode
            last_stdout = cp.stdout or ""
            last_stderr = cp.stderr or ""
            if cp.returncode == 0:
                break
        except subprocess.TimeoutExpired as e:
            last_rc = 124
            last_stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
            last_stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""

        if i < retries:
            time.sleep(backoff)
            backoff *= backoff_mult

    elapsed_s = time.monotonic() - start
    if last is not None:
        return RunResult(
            returncode=last.returncode,
            stdout=last_stdout,
            stderr=last_stderr,
            attempts=attempts,
            elapsed_s=elapsed_s,
        )
    return RunResult(
        returncode=last_rc,
        stdout=last_stdout,
        stderr=last_stderr,
        attempts=attempts,
        elapsed_s=elapsed_s,
    )

