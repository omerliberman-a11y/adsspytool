"""Entrypoint: `python -m adspy.queue` starts the worker.

Using a __main__.py (instead of `python -m adspy.queue.worker`) avoids the
classic Python double-import trap where __main__ and the module under its
package path become two separate namespaces — handlers registered into one
wouldn't be visible to the other.
"""
import sys

# Windows cp1252 console can't encode emoji/non-ASCII characters from ad copy,
# crashing the worker on `log.info(...)`. Force UTF-8 on stdout/stderr.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from adspy.queue.worker import Worker  # noqa: E402

if __name__ == "__main__":
    Worker().run()
