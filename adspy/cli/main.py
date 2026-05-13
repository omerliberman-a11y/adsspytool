from typing import Annotated

import typer
from sqlalchemy import select

from adspy.config import get_settings
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.scrapers.base import ScrapeQuery
from adspy.services.ingestion import ingest_meta
from adspy.utils.logging import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)
scrape_app = typer.Typer(no_args_is_help=True, help="Run platform scrapers")
ads_app = typer.Typer(no_args_is_help=True, help="Query stored ads")
app.add_typer(scrape_app, name="scrape")
app.add_typer(ads_app, name="ads")


@app.callback()
def _init() -> None:
    s = get_settings()
    configure_logging(level=s.log_level, json=s.log_json)


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
    result = ingest_meta(query)
    typer.echo(
        f"fetched={result.fetched} "
        f"normalized={result.normalized} "
        f"upserted={result.upserted} "
        f"errors={result.errors}"
    )


@ads_app.command("list")
def ads_list_cmd(
    platform: Annotated[str | None, typer.Option(help="Filter by platform")] = None,
    min_score: Annotated[int, typer.Option(help="Minimum winner_score")] = 0,
    limit: Annotated[int, typer.Option(help="Max rows")] = 25,
) -> None:
    stmt = select(Ad)
    if platform:
        stmt = stmt.where(Ad.platform == platform)
    if min_score > 0:
        stmt = stmt.where(Ad.winner_score >= min_score)
    stmt = stmt.order_by(Ad.winner_score.desc().nullslast()).limit(limit)

    with session_scope() as s:
        rows = list(s.scalars(stmt))

    if not rows:
        typer.echo("(no ads)")
        return
    for a in rows:
        typer.echo(
            f"{a.platform:<6} score={a.winner_score:>3} "
            f"days={a.days_active!s:<5} variants={a.variant_count!s:<3} "
            f"{(a.advertiser_name or '?')[:30]:<30} "
            f"{(a.headline or a.primary_text or '')[:60]}"
        )


if __name__ == "__main__":
    app()
