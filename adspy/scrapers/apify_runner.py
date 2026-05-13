from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from apify_client import ApifyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from adspy.config import Settings, get_settings
from adspy.db.session import session_scope
from adspy.models.apify_run import ApifyRun
from adspy.utils.errors import CostCapExceeded, ScrapeError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class RunResult:
    run_id: str
    dataset_id: str
    item_count: int
    cost_usd: float | None
    duration_secs: float


class ApifyRunner:
    """Calls an Apify actor, persists the run record, and yields dataset items.

    One ApifyRun row is written per call (even on failure) so we have a cost+replay trail.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = ApifyClient(self.settings.apify_token.get_secret_value())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    def run(
        self,
        actor_id: str,
        platform: str,
        run_input: dict[str, Any],
        timeout_secs: int | None = None,
    ) -> RunResult:
        started = datetime.now(UTC)
        record = ApifyRun(
            actor_id=actor_id,
            platform=platform,
            input_json=run_input,
            status="running",
            started_at=started,
        )
        with session_scope() as s:
            s.add(record)
            s.flush()
            run_record_id = record.id

        try:
            actor = self._client.actor(actor_id)
            run = actor.call(
                run_input=run_input,
                timeout_secs=timeout_secs or self.settings.apify_timeout_secs,
            )
            if run is None:
                raise ScrapeError(f"Apify actor {actor_id} returned no run")

            cost = float(run.get("usage", {}).get("ACTOR_COMPUTE_UNITS_USD", 0.0) or 0.0)
            if cost > self.settings.apify_max_usd_per_run:
                raise CostCapExceeded(
                    f"Apify run {run['id']} cost ${cost:.2f} > cap "
                    f"${self.settings.apify_max_usd_per_run:.2f}"
                )

            dataset_id = run["defaultDatasetId"]
            dataset = self._client.dataset(dataset_id)
            item_count = int(dataset.get().get("itemCount", 0))  # type: ignore[union-attr]

            duration = (datetime.now(UTC) - started).total_seconds()

            self._finalize(
                run_record_id,
                status="ok",
                run_id=run["id"],
                dataset_id=dataset_id,
                cost_usd=cost,
                duration_secs=duration,
                item_count=item_count,
                error=None,
            )

            log.info(
                "apify_run_ok",
                actor=actor_id,
                platform=platform,
                run_id=run["id"],
                items=item_count,
                cost=cost,
            )
            return RunResult(
                run_id=run["id"],
                dataset_id=dataset_id,
                item_count=item_count,
                cost_usd=cost,
                duration_secs=duration,
            )
        except CostCapExceeded as exc:
            duration = (datetime.now(UTC) - started).total_seconds()
            self._finalize(
                run_record_id,
                status="cost_cap",
                run_id=None,
                dataset_id=None,
                cost_usd=None,
                duration_secs=duration,
                item_count=None,
                error=str(exc),
            )
            raise
        except Exception as exc:
            duration = (datetime.now(UTC) - started).total_seconds()
            self._finalize(
                run_record_id,
                status="error",
                run_id=None,
                dataset_id=None,
                cost_usd=None,
                duration_secs=duration,
                item_count=None,
                error=str(exc),
            )
            log.error("apify_run_failed", actor=actor_id, platform=platform, error=str(exc))
            raise ScrapeError(f"Apify actor {actor_id} failed: {exc}") from exc

    def iter_dataset(self, dataset_id: str) -> Iterator[dict[str, Any]]:
        for item in self._client.dataset(dataset_id).iterate_items():
            yield item

    def _finalize(
        self,
        record_id: int,
        *,
        status: str,
        run_id: str | None,
        dataset_id: str | None,
        cost_usd: float | None,
        duration_secs: float,
        item_count: int | None,
        error: str | None,
    ) -> None:
        with session_scope() as s:
            row = s.get(ApifyRun, record_id)
            if row is None:
                return
            row.status = status
            row.run_id = run_id
            row.dataset_id = dataset_id
            row.cost_usd = cost_usd
            row.duration_secs = duration_secs
            row.item_count = item_count
            row.error_message = error
            row.finished_at = datetime.now(UTC)
