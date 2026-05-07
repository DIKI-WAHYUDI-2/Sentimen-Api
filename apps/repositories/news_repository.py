from datetime import datetime
import logging

from sqlalchemy import func

from apps.app import db
from apps.models.news import News

logger = logging.getLogger(__name__)


class NewsRepository:
    @staticmethod
    def save(news_item):
        try:
            db.session.add(news_item)
            db.session.commit()
            logger.debug("News item saved successfully")
            return news_item
        except Exception:
            db.session.rollback()
            logger.exception("Failed to save news item")
            return None

    @staticmethod
    def create(news_data):
        published_at = news_data.get("published_at") or news_data.get("date")
        if not published_at:
            raise ValueError("published_at is required")

        news_item = News(
            title=news_data.get("title"),
            published_at=datetime.strptime(published_at, "%Y-%m-%d").date(),
            source=news_data.get("source"),
            url=news_data.get("url"),
            content=news_data.get("content"),
            sentiment=news_data.get("sentiment"),
        )
        return NewsRepository.save(news_item)

    @staticmethod
    def find_all():
        return News.query.all()

    @staticmethod
    def find_paginated(page, limit):
        query = News.query.order_by(News.published_at.desc(), News.id.desc())
        return query.paginate(page=page, per_page=limit, error_out=False)

    @staticmethod
    def find_by_id(news_id):
        return News.query.get(news_id)

    @staticmethod
    def delete(news_id):
        news_item = News.query.get(news_id)
        if not news_item:
            return None

        try:
            db.session.delete(news_item)
            db.session.commit()
            logger.debug("News item deleted successfully", extra={"news_id": news_id})
            return news_item
        except Exception:
            db.session.rollback()
            logger.exception("Failed to delete news item", extra={"news_id": news_id})
            return None

    @staticmethod
    def find_by_url(url):
        if not url:
            return None
        return News.query.filter(News.url == url).first()

    @staticmethod
    def find_by_keyword(keyword):
        pattern = f"%{keyword}%"
        return (
            News.query.filter(News.title.ilike(pattern))
            .order_by(News.published_at.desc(), News.id.desc())
            .all()
        )

    @staticmethod
    def get_sentiment_data():
        try:
            results = (
                db.session.query(News.sentiment, func.count(News.sentiment))
                .group_by(News.sentiment)
                .all()
            )
            return [{"name": sentiment.capitalize(), "value": count} for sentiment, count in results]
        except Exception:
            logger.exception("Failed to load sentiment data")
            return []

    @staticmethod
    def find_by_month_range(start_year, start_month, end_year, end_month):
        try:
            from sqlalchemy import extract, and_, or_
            results = (
                News.query
                .filter(
                    or_(
                        # Years between start and end exclusively
                        and_(
                            extract('year', News.published_at) > start_year,
                            extract('year', News.published_at) < end_year,
                        ),
                        # Same year as start, month >= start_month (only if start==end year)
                        and_(
                            extract('year', News.published_at) == start_year,
                            extract('year', News.published_at) == end_year,
                            extract('month', News.published_at) >= start_month,
                            extract('month', News.published_at) <= end_month,
                        ),
                        # Start year, any month >= start_month (when start != end year)
                        and_(
                            extract('year', News.published_at) == start_year,
                            extract('year', News.published_at) != end_year,
                            extract('month', News.published_at) >= start_month,
                        ),
                        # End year, any month <= end_month (when start != end year)
                        and_(
                            extract('year', News.published_at) == end_year,
                            extract('year', News.published_at) != start_year,
                            extract('month', News.published_at) <= end_month,
                        ),
                    )
                )
                .order_by(News.published_at.asc(), News.id.asc())
                .all()
            )
            return results
        except Exception:
            logger.exception("Failed to find news by month range")
            return []

    @staticmethod
    def get_sentiment_and_date():
        try:
            return db.session.query(
                func.date(News.published_at).label("published_at"),
                News.sentiment,
            ).all()
        except Exception:
            logger.exception("Failed to load sentiment timeline data")
            return []

    @staticmethod
    def get_available_years():
        try:
            rows = (
                db.session.query(func.extract("year", News.published_at).label("year"))
                .filter(News.published_at.isnot(None))
                .distinct()
                .order_by(func.extract("year", News.published_at).desc())
                .all()
            )
            return [int(row.year) for row in rows if row.year is not None]
        except Exception:
            logger.exception("Failed to load available news years")
            return []

    @staticmethod
    def get_sentiment_and_date_by_year(year):
        try:
            return (
                db.session.query(
                    func.date(News.published_at).label("published_at"),
                    News.sentiment,
                )
                .filter(func.extract("year", News.published_at) == year)
                .all()
            )
        except Exception:
            logger.exception("Failed to load sentiment timeline data by year", extra={"year": year})
            return []
