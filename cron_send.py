"""Run send-avymail.py and send a failure report if the run does not complete.

The crontab runs this script. It reports these failures:
- send-avymail.py exits with an error, for example a crash at startup.
- The operating system stops send-avymail.py, for example when memory is full.
- send-avymail.py runs longer than TIMEOUT_SECONDS.

If send-avymail.py exits with REPORTED_EXIT_CODE, it already sent a report for
its per-recipient failures, and this script sends no report.
"""

import collections
import os
import subprocess
import sys
import threading

from failure_report import REPORTED_EXIT_CODE, send_failure_email

# A normal run takes less than one minute. Stop the run before the next one.
TIMEOUT_SECONDS = 10 * 60
# The number of output lines to include in the report.
OUTPUT_LINES = 200


def main() -> int:
    cmd = [sys.executable, "send-avymail.py", *sys.argv[1:]]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    timed_out = threading.Event()

    def stop_run():
        timed_out.set()
        proc.kill()

    timer = threading.Timer(TIMEOUT_SECONDS, stop_run)
    timer.start()

    # Show each line in the log as it arrives, and keep the last lines for the report.
    tail: collections.deque = collections.deque(maxlen=OUTPUT_LINES)
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="", flush=True)
        tail.append(line)
    exit_code = proc.wait()
    timer.cancel()

    if exit_code == 0 or (exit_code == REPORTED_EXIT_CODE and not timed_out.is_set()):
        return exit_code

    if timed_out.is_set():
        reason = (
            f"The run did not complete in {TIMEOUT_SECONDS} seconds and was stopped."
        )
    elif exit_code < 0:
        reason = f"The run was stopped by signal {-exit_code}."
    else:
        reason = f"The run exited with code {exit_code}."

    body = f"{reason}\n\nLast {len(tail)} lines of output:\n\n" + "".join(tail)
    send_failure_email(1, body)
    return exit_code if exit_code > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
