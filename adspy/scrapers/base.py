from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScrapeQuery:
    keyword: str | None = None
    advertiser_page: str | None = None
    countries: tuple[str, ...] = field(default_factory=tuple)
    active_only: bool = True
    limit: int = 200

    def __post_init__(self) -> None:
        if not self.keyword and not self.advertiser_page:
            raise ValueError("ScrapeQuery requires keyword or advertiser_page")
