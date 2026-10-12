import sqlite3
import httpx
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .analytics import Analytics
from .db import SCHEMA_VERSION, connect
from .schemas import (AnalyticsResponse, Category, DataQuality, ErrorResponse, FilterOptions,
                      Filters, OptionQuery, Overview, Ratings, ReviewQuery, ReviewsResponse, Sentiments, Topics, Review, Insights,
                      TranslationRequest, TranslationsResponse, Priorities)
from .services.topics import TOPICS
from .services.insights import build_catalog,generate_insights
from .services.translations import translate_reviews, TranslationUnavailable

router = APIRouter(prefix='/api', responses={503: {'model': ErrorResponse}})


def snapshot(request: Request):
    path = request.app.state.settings.database_path
    try:
        with connect(path, readonly=True) as connection:
            connection.execute('BEGIN')
            if connection.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
                raise HTTPException(503, 'Database is not ready')
            state = connection.execute('SELECT * FROM import_state WHERE id=1').fetchone()
            if state is None or connection.execute('SELECT COUNT(*) FROM reviews').fetchone()[0] != state['row_count']:
                raise HTTPException(503, 'Database is not ready')
            yield connection, state
    except (sqlite3.Error, OSError):
        raise HTTPException(503, 'Database is not ready') from None


def analytics(filters: Annotated[Filters, Query()], db=Depends(snapshot)):
    return Analytics(*db, filters)


def response(service, data):
    return {'data': data, 'meta': service.meta()}


@router.get('/overview', response_model=AnalyticsResponse[Overview])
def overview(service=Depends(analytics)):
    return response(service, service.overview())


@router.get('/ratings', response_model=AnalyticsResponse[Ratings])
def ratings(service=Depends(analytics)):
    return response(service, service.ratings())


@router.get('/categories', response_model=AnalyticsResponse[list[Category]])
def categories(service=Depends(analytics)):
    return response(service, service.categories())


@router.get('/reviews', response_model=ReviewsResponse)
def reviews(query: Annotated[ReviewQuery, Query()], db=Depends(snapshot)):
    filters = Filters(**query.model_dump(exclude={'page','page_size'}))
    return Analytics(*db, filters).reviews(query.page, query.page_size)


@router.post('/reviews/translations', response_model=TranslationsResponse)
def review_translations(query:TranslationRequest, request:Request, db=Depends(snapshot)):
    placeholders=','.join('?' for _ in query.review_ids)
    rows=db[0].execute(f'SELECT review_id,title,review_text_clean AS review_text FROM reviews WHERE review_id IN ({placeholders})',query.review_ids).fetchall()
    if len(rows)!=len(query.review_ids): raise HTTPException(404,'Review not found')
    lookup={row['review_id']:dict(row) for row in rows}
    items=[lookup[identifier] for identifier in query.review_ids]
    db[0].rollback()
    try:
        return translate_reviews(items,db[1]['dataset_sha256'],request.app.state.settings)
    except TranslationUnavailable:
        raise HTTPException(503,'Translation service is not configured') from None
    except httpx.TimeoutException:
        raise HTTPException(504,'Translation timed out') from None
    except httpx.HTTPError:
        raise HTTPException(502,'Translation provider is unavailable') from None
    except (ValueError,TypeError,KeyError):
        raise HTTPException(502,'Translation output could not be validated') from None
    except sqlite3.Error:
        raise HTTPException(503,'Translation cache is unavailable') from None


@router.get('/data-quality', response_model=AnalyticsResponse[DataQuality])
def quality(service=Depends(analytics)):
    return response(service, service.quality())


@router.get('/filter-options', response_model=AnalyticsResponse[FilterOptions])
def options(query: Annotated[OptionQuery, Query()], db=Depends(snapshot)):
    service = Analytics(*db, Filters(department=query.department))
    return response(service, service.options())


@router.get('/sentiments', response_model=AnalyticsResponse[Sentiments])
def sentiments(service=Depends(analytics)):
    return response(service,service.sentiments())


@router.get('/topics', response_model=AnalyticsResponse[Topics])
def topics(service=Depends(analytics)):
    return response(service,service.topics())


@router.get('/topics/{topic}/examples', response_model=AnalyticsResponse[list[Review]], responses={404:{'model':ErrorResponse}})
def topic_examples(topic:str,service=Depends(analytics)):
    if topic not in TOPICS: raise HTTPException(404,'Unknown topic')
    return response(service,service.topic_examples(topic))


@router.post('/insights',response_model=AnalyticsResponse[Insights])
def insights(filters:Filters,request:Request,db=Depends(snapshot)):
    service=Analytics(*db,filters)
    catalog=build_catalog(service)
    # Release the read transaction before the bounded remote call.
    db[0].rollback()
    return {'data':generate_insights(catalog,request.app.state.settings),'meta':catalog['meta']}


@router.get('/priorities',response_model=AnalyticsResponse[Priorities])
def priorities(service=Depends(analytics)):
    return response(service,service.priorities())
