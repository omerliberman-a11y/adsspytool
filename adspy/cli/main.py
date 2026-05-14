from typing import Annotated

import typer
from sqlalchemy import select

from adspy.config import get_settings
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.queue.enqueue import enqueue
from adspy.scrapers.base import ScrapeQuery
from adspy.services.ingestion import ingest_meta
from adspy.utils.logging import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)
scrape_app = typer.Typer(no_args_is_help=True, help="Run platform scrapers")
ads_app = typer.Typer(no_args_is_help=True, help="Query stored ads")
queue_app = typer.Typer(no_args_is_help=True, help="Inspect / drive the task queue")
analyze_app = typer.Typer(no_args_is_help=True, help="AI analysis + embeddings")
app.add_typer(scrape_app, name="scrape")
app.add_typer(ads_app, name="ads")
app.add_typer(queue_app, name="queue")
app.add_typer(analyze_app, name="ai")


@app.callback()
def _init() -> None:
    s = get_settings()
    configure_logging(level=s.log_level, json=s.log_json)


# ---- scrape ----
@scrape_app.command("meta")
def scrape_meta_cmd(
    keyword: Annotated[str | None, typer.Option(help="Keyword to search for")] = None,
    advertiser_page: Annotated[
        str | None, typer.Option("--page", help="Facebook page_id to scrape")
    ] = None,
    country: Annotated[
        list[str], typer.Option("--country", help="Country code (repeatable)")
    ] = [],
    limit: Annotated[int, typer.Option(help="Max ads to scrape")] = 200,
    active_only: Annotated[bool, typer.Option(help="Only scrape currently-active ads")] = True,
    enqueue_followups: Annotated[
        bool, typer.Option(help="Enqueue snapshot/analyze/embed tasks for new ads")
    ] = True,
) -> None:
    if not keyword and not advertiser_page:
        raise typer.BadParameter("--keyword or --page is required")
    query = ScrapeQuery(
        keyword=keyword,
        advertiser_page=advertiser_page,
        countries=tuple(country),
        active_only=active_only,
        limit=limit,
    )
    result = ingest_meta(query, enqueue_followups=enqueue_followups)
    typer.echo(
        f"fetched={result.fetched} normalized={result.normalized} "
        f"recovered={result.recovered} upserted={result.upserted} errors={result.errors}"
    )


# ---- ads ----
@ads_app.command("list")
def ads_list_cmd(
    platform: Annotated[str | None, typer.Option(help="Filter by platform")] = None,
    min_score: Annotated[int, typer.Option(help="Minimum winner_score")] = 0,
    hook: Annotated[str | None, typer.Option(help="Filter by hook_type")] = None,
    limit: Annotated[int, typer.Option(help="Max rows")] = 25,
) -> None:
    stmt = select(Ad)
    if platform:
        stmt = stmt.where(Ad.platform == platform)
    if min_score > 0:
        stmt = stmt.where(Ad.winner_score >= min_score)
    if hook:
        stmt = stmt.where(Ad.hook_type == hook)
    stmt = stmt.order_by(Ad.winner_score.desc().nullslast()).limit(limit)

    with session_scope() as s:
        rows = list(s.scalars(stmt))

    if not rows:
        typer.echo("(no ads)")
        return
    for a in rows:
        typer.echo(
            f"{a.platform:<6} score={a.winner_score:>3} "
            f"hook={(a.hook_type or '-'):<14} "
            f"days={a.days_active!s:<5} variants={a.variant_count!s:<3} "
            f"{(a.advertiser_name or '?')[:25]:<25} "
            f"{(a.ai_hook or a.headline or a.primary_text or '')[:60]}"
        )


# ---- queue ----
@queue_app.command("worker")
def queue_worker_cmd() -> None:
    """Run the task-queue worker loop (foreground)."""
    from adspy.queue.worker import Worker

    Worker().run()


@queue_app.command("status")
def queue_status_cmd() -> None:
    from sqlalchemy import func

    from adspy.models.task import Task

    with session_scope() as s:
        rows = s.execute(
            select(Task.status, func.count()).group_by(Task.status).order_by(Task.status)
        ).all()
    if not rows:
        typer.echo("(no tasks)")
        return
    for status, count in rows:
        typer.echo(f"{status:<12} {count}")


@queue_app.command("enqueue")
def queue_enqueue_cmd(
    kind: Annotated[str, typer.Argument(help="Task kind")],
    payload: Annotated[str, typer.Option(help="JSON payload string")] = "{}",
) -> None:
    import json

    task_id = enqueue(kind, json.loads(payload))
    typer.echo(f"task_id={task_id}")


# ---- ai ----
@analyze_app.command("analyze")
def ai_analyze_cmd(
    platform: Annotated[str, typer.Option(help="Platform")] = "meta",
    ad_id: Annotated[str | None, typer.Option(help="Specific ad_id (analyze just this)")] = None,
    limit: Annotated[int, typer.Option(help="Batch size when no ad_id")] = 25,
) -> None:
    from adspy.ai.analysis import analyze_batch, analyze_one

    if ad_id:
        analyze_one(platform=platform, ad_id=ad_id)
        typer.echo(f"done: {platform}/{ad_id}")
    else:
        n = analyze_batch(limit=limit)
        typer.echo(f"analyzed: {n}")


@analyze_app.command("embed")
def ai_embed_cmd(
    platform: Annotated[str, typer.Option(help="Platform")] = "meta",
    ad_id: Annotated[str | None, typer.Option(help="Specific ad_id")] = None,
    limit: Annotated[int, typer.Option(help="Batch size")] = 50,
) -> None:
    from adspy.embeddings.embed_ad import embed_one

    if ad_id:
        embed_one(platform=platform, ad_id=ad_id)
        typer.echo(f"done: {platform}/{ad_id}")
        return

    stmt = (
        select(Ad.platform, Ad.ad_id)
        .where(Ad.platform == platform, Ad.copy_embedding.is_(None))
        .limit(limit)
    )
    with session_scope() as s:
        rows = list(s.execute(stmt))
    for p, aid in rows:
        try:
            embed_one(platform=p, ad_id=aid)
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"  fail {p}/{aid}: {exc}", err=True)
    typer.echo(f"embedded: {len(rows)}")


@analyze_app.command("daily-snapshot")
def ai_daily_snapshot_cmd() -> None:
    from adspy.services.daily_snapshot import run_daily_snapshot

    n = run_daily_snapshot()
    typer.echo(f"snapshot_rows: {n}")


@analyze_app.command("rip-off-scan")
def ai_rip_off_scan_cmd() -> None:
    from adspy.services.rip_off import scan_for_rip_offs

    n = scan_for_rip_offs()
    typer.echo(f"cross-advertiser clusters: {n}")


if __name__ == "__main__":
    app()
