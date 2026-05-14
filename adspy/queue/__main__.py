"""Entrypoint: `python -m adspy.queue` starts the worker.

Using a __main__.py (instead of `python -m adspy.queue.worker`) avoids the
classic Python double-import trap where __main__ and the module under its
package path become two separate namespaces — handlers registered into one
wouldn't be visible to the other.
"""
from adspy.queue.worker import Worker

if __name__ == "__main__":
    Worker().run()
