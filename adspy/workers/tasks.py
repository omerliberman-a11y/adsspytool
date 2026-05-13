from adspy.scrapers.base import ScrapeQuery
from adspy.services.ingestion import IngestionResult, ingest_meta
from adspy.workers.app import app


@app.task(name="adspy.scrape_meta")
def scrape_meta_task(
    keyword: str | None = None,
    advertiser_page: str | None = None,
    countries: list[str] | None = None,
    active_only: bool = True,
    limit: int = 200,
) -> dict[str, int | str]:
    query = ScrapeQuery(
        keyword=keyword,
        advertiser_page=advertiser_page,
        countries=tuple(countries or ()),
        active_only=active_only,
        limit=limit,
    )
    result: IngestionResult = ingest_meta(query)
    return {
        "platform": result.platform,
        "fetched": result.fetched,
        "normalized": result.normalized,
        "upserted": result.upserted,
        "scored": result.scored,
        "errors": result.errors,
    }
