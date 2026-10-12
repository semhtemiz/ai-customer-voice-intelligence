from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sentiment = Literal['positive', 'neutral', 'negative', 'unknown']


class Filters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    department: str | None = Field(default=None, max_length=100)
    class_name: str | None = Field(default=None, max_length=100)
    rating: int | None = Field(default=None, ge=1, le=5)
    sentiment: Sentiment | None = None
    search: str | None = Field(default=None, max_length=200)

    @field_validator('department', 'class_name', 'search', mode='after')
    @classmethod
    def normalize(cls, value):
        return value.strip() or None if value is not None else None


class ReviewQuery(Filters):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class OptionQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    department: str | None = Field(default=None, max_length=100)

    @field_validator('department')
    @classmethod
    def normalize(cls, value):
        return value.strip() or None if value is not None else None


class Meta(BaseModel):
    dataset_sha256: str
    filters: Filters
    matched_review_count: int
    text_review_count: int
    sentiment_classified_count: int
    sentiment_method: str | None
    sentiment_run_id: str | None
    topic_run_id: str | None
    limitations: list[str]
    sentiment_model_id: str | None = None
    sentiment_model_revision: str | None = None
    sentiment_eligible_count: int = 0
    sentiment_processed_count: int = 0
    topic_method: str | None = None
    taxonomy_version: str | None = None


class SentimentBin(BaseModel):
    sentiment: Sentiment
    reviews: int


class Sentiments(BaseModel):
    distribution: list[SentimentBin]
    classified_count: int
    text_review_count: int


class TopicBin(BaseModel):
    topic: str
    mentions: int
    rate_pct: float | None


class Topics(BaseModel):
    distribution: list[TopicBin]
    candidate_count: int
    topic_processed_count: int
    topic_failed_count: int
    topic_pending_count: int


T = TypeVar('T')


class AnalyticsResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta


class Overview(BaseModel):
    model_config = ConfigDict(json_schema_extra={'examples': [{
        'total_reviews': 0, 'valid_rating_count': 0, 'valid_recommendation_count': 0,
        'avg_rating': None, 'recommendation_rate_pct': None, 'low_rating_rate_pct': None,
    }]})
    total_reviews: int
    valid_rating_count: int
    valid_recommendation_count: int
    avg_rating: float | None
    recommendation_rate_pct: float | None
    low_rating_rate_pct: float | None


class RatingBin(BaseModel):
    rating: int
    reviews: int


class Ratings(BaseModel):
    distribution: list[RatingBin]
    valid_rating_count: int
    invalid_or_missing_rating_count: int


class Category(BaseModel):
    department: str
    reviews: int
    valid_rating_count: int
    avg_rating: float | None
    low_rating_rate_pct: float | None


class Review(BaseModel):
    review_id: int
    clothing_id: int | None
    title: str | None
    review_text: str | None
    rating: int | None
    recommended_ind: int | None
    positive_feedback_count: int | None
    division_name: str
    department_name: str
    class_name: str
    sentiment: Sentiment
    sentiment_score: float | None
    complaint_topics: list[str]


class ReviewsResponse(BaseModel):
    items: list[Review]
    page: int
    page_size: int
    total: int
    total_pages: int
    meta: Meta


class TranslationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    review_ids: list[Annotated[int, Field(strict=True, ge=0)]] = Field(min_length=1, max_length=5)

    @field_validator('review_ids')
    @classmethod
    def unique_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('Review IDs must be unique')
        return value


class ReviewTranslation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    review_id: int
    title: str | None = Field(max_length=4000)
    review_text: str | None = Field(max_length=60000)


class TranslationsResponse(BaseModel):
    items: list[ReviewTranslation]
    language: Literal['tr'] = 'tr'
    model: str


class ImportKpis(Overview):
    text_review_count: int


class ImportReport(BaseModel):
    file: str
    sha256: str
    row_count: int
    columns: list[str]
    blank_counts: dict[str, int]
    invalid_source_id_count: int
    duplicate_source_id_count: int
    duplicate_content_excess_count: int
    invalid_rating_count: int
    invalid_recommendation_count: int
    invalid_age_count: int
    age_range: list[int] | None
    rating_counts: dict[str, int]
    department_counts: dict[str, int]
    kpis: ImportKpis


class FilteredQuality(BaseModel):
    review_count: int
    missing_text_count: int
    missing_title_count: int
    invalid_or_missing_rating_count: int
    invalid_or_missing_recommendation_count: int
    invalid_or_missing_age_count: int
    missing_division_count: int
    missing_department_count: int
    missing_class_count: int


class DataQuality(BaseModel):
    import_report: ImportReport
    imported_at: str
    filtered_quality: FilteredQuality


class FilterOptions(BaseModel):
    departments: list[str]
    classes: list[str]
    ratings: list[int]
    sentiments: list[Sentiment]


class ProductPriority(BaseModel):
    clothing_id: int
    reviews: int
    valid_rating_count: int
    avg_rating: float | None
    low_rating_count: int
    low_rating_rate_pct: float
    topics: list[dict[str, str | int]]


class Priorities(BaseModel):
    minimum_product_ratings: int
    products: list[ProductPriority]
    disagreement_count: int
    compared_count: int
    disagreement_examples: list[Review]


class ErrorResponse(BaseModel):
    detail: str


class Evidence(BaseModel):
    id: str
    metric: str
    value: float | int | None
    denominator: int | None
    review_ids: list[int]


class InsightStatement(BaseModel):
    text: str
    evidence_ids: list[str]


class Insights(BaseModel):
    headline: str
    key_findings: list[InsightStatement]
    recommended_actions: list[InsightStatement]
    evidence: list[Evidence]
    limitations: list[str]
    source: Literal['llm','rules','empty']
    fallback_reason: Literal['not_configured','timeout','provider_error','invalid_output'] | None
