"""One filtered CTE and one read snapshot shared by every analytical query."""
import json
import re
from pathlib import Path

from .schemas import Filters
from .services.topics import TOPICS, has_explicit_complaint

SQL_DIR = Path(__file__).resolve().parents[1] / 'sql'


def escape_like(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def mask_text(text):
    if text is None:
        return None
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', '[email]', text)
    # Conservative phone masking; this is a baseline, not exhaustive PII detection.
    return re.sub(r'(?<!\w)\+?\d[\d ().-]{7,}\d(?!\w)', '[phone]', text)


class Analytics:
    def __init__(self, connection, state, filters: Filters):
        self.connection = connection
        connection.create_function('topic_concern',1,has_explicit_complaint,deterministic=True)
        self.state = state
        self.filters = filters
        self.limitations = ['No review dates or sales amounts are available.',
                            'Displayed review text uses baseline email/phone masking; it is not exhaustive PII detection.']
        self.sentiment_run = self.selected_run(state['selected_sentiment_run_id'], 'sentiment')
        self.topic_run = self.selected_run(state['selected_topic_run_id'], 'topics')
        if self.topic_run and self.topic_run['source_sentiment_run_id'] != (
            self.sentiment_run['run_id'] if self.sentiment_run else None
        ):
            self.topic_run = None
            self.limitations.append('Topic run does not match the selected sentiment run and is excluded.')
        if not self.sentiment_run:
            self.limitations.append('No compatible completed sentiment analysis is selected; predictions are unknown.')
        elif self.sentiment_run['method'] == 'rating_heuristic':
            self.limitations.append('Sentiment uses a rating heuristic, not an NLP model.')
        elif self.sentiment_run['model_id'] == 'cardiffnlp/twitter-roberta-base-sentiment-latest':
            self.limitations.append('The sentiment model was trained on English tweets, not clothing reviews; inputs are truncated to 256 tokens.')
        if self.topic_run:
            self.limitations.append('Topics use a keyword baseline: negation, context and implicit complaints may be missed. Counts are observed labels, not ground truth.')
        self.params = {'sentiment_run_id': self.sentiment_run['run_id'] if self.sentiment_run else None}
        conditions = []
        for parameter, column in (('department', 'department_name'), ('class_name', 'class_name')):
            value = getattr(filters, parameter)
            if value is not None:
                conditions.append(f"COALESCE({column}, 'Unknown') = :{parameter}")
                self.params[parameter] = value
        if filters.rating is not None:
            conditions.append('rating = :rating')
            self.params['rating'] = filters.rating
        if filters.sentiment is not None:
            conditions.append('sentiment = :sentiment')
            self.params['sentiment'] = filters.sentiment
        if filters.search is not None:
            conditions.append("(COALESCE(title,'') LIKE :search ESCAPE '\\' OR COALESCE(review_text_clean,'') LIKE :search ESCAPE '\\')")
            self.params['search'] = '%' + escape_like(filters.search) + '%'
        where = ' AND '.join(conditions) or '1=1'
        self.cte = """WITH enriched_reviews AS (
            SELECT r.*, CASE WHEN r.review_text_clean IS NOT NULL
                THEN COALESCE(p.sentiment,'unknown') ELSE 'unknown' END AS sentiment,
                CASE WHEN r.review_text_clean IS NOT NULL THEN p.score END AS sentiment_score
            FROM reviews r LEFT JOIN review_predictions p
                ON p.review_id=r.review_id AND p.run_id=:sentiment_run_id
        ), filtered_reviews AS (SELECT * FROM enriched_reviews WHERE """ + where + ') '

    def selected_run(self, run_id, kind):
        if run_id is None:
            return None
        result = self.connection.execute("""SELECT * FROM analysis_runs
            WHERE run_id=? AND kind=? AND status='completed' AND dataset_sha256=?""",
            (run_id, kind, self.state['dataset_sha256'])).fetchone()
        if result is None:
            self.limitations.append(f'Incompatible selected {kind} run is excluded.')
        return result

    def query(self, sql, **extra):
        return self.connection.execute(self.cte + sql, self.params | extra)

    def meta(self):
        counts = self.query("""SELECT COUNT(*) matched_review_count,
            COUNT(review_text_clean) text_review_count,
            COUNT(CASE WHEN sentiment IN ('positive','neutral','negative')
                THEN 1 END) sentiment_classified_count FROM filtered_reviews""").fetchone()
        limitations = list(self.limitations)
        if self.sentiment_run and counts['sentiment_classified_count'] < counts['text_review_count']:
            limitations.append('Sentiment coverage is partial for the matched text reviews.')
        return dict(counts) | {
            'dataset_sha256': self.state['dataset_sha256'], 'filters': self.filters.model_dump(),
            'sentiment_method': self.sentiment_run['method'] if self.sentiment_run else None,
            'sentiment_run_id': self.sentiment_run['run_id'] if self.sentiment_run else None,
            'topic_run_id': self.topic_run['run_id'] if self.topic_run else None,
            'limitations': limitations,
            'sentiment_model_id': self.sentiment_run['model_id'] if self.sentiment_run else None,
            'sentiment_model_revision': self.sentiment_run['model_revision'] if self.sentiment_run else None,
            'sentiment_eligible_count': self.sentiment_run['eligible_count'] if self.sentiment_run else 0,
            'sentiment_processed_count': self.sentiment_run['processed_count'] if self.sentiment_run else 0,
            'topic_method': self.topic_run['method'] if self.topic_run else None,
            'taxonomy_version': self.topic_run['taxonomy_version'] if self.topic_run else None,
        }

    def sentiments(self):
        counts={r['sentiment']:r['reviews'] for r in self.query('SELECT sentiment,COUNT(*) reviews FROM filtered_reviews GROUP BY sentiment')}
        meta=self.meta()
        return {'distribution':[{'sentiment':label,'reviews':counts.get(label,0)} for label in ('positive','neutral','negative','unknown')],
                'classified_count':meta['sentiment_classified_count'],'text_review_count':meta['text_review_count']}

    def candidate_query(self, sql, **extra):
        concern = " OR topic_concern(review_text_clean)=1" if not self.topic_run or self.topic_run['taxonomy_version']=='clothing-phrases-v2' else ''
        cte=self.cte.rstrip()+", filtered_candidates AS (SELECT * FROM filtered_reviews WHERE review_text_clean IS NOT NULL AND (rating<=2 OR sentiment='negative'"+concern+")) "
        return self.connection.execute(cte+sql,self.params|extra)

    def topics(self):
        run_id=self.topic_run['run_id'] if self.topic_run else None
        counts=self.candidate_query("""SELECT COUNT(*) candidate_count,
            COUNT(CASE WHEN tr.status='completed' THEN 1 END) topic_processed_count,
            COUNT(CASE WHEN tr.status='failed' THEN 1 END) topic_failed_count
            FROM filtered_candidates fc LEFT JOIN review_topic_results tr ON tr.review_id=fc.review_id AND tr.run_id=:topic_run_id""",topic_run_id=run_id).fetchone()
        data=dict(counts); data['topic_pending_count']=data['candidate_count']-data['topic_processed_count']-data['topic_failed_count']
        bins={r['topic']:r['mentions'] for r in self.candidate_query((SQL_DIR/'03_topics.sql').read_text(),topic_run_id=run_id)}
        denominator=data['topic_processed_count']
        data['distribution']=[{'topic':topic,'mentions':bins.get(topic,0),'rate_pct':round(100*bins.get(topic,0)/denominator,2) if denominator else None} for topic in TOPICS]
        return data

    def topic_examples(self, topic):
        run_id=self.topic_run['run_id'] if self.topic_run else None
        ids=[r[0] for r in self.candidate_query("""SELECT fc.review_id FROM filtered_candidates fc
            JOIN review_topics rt ON rt.review_id=fc.review_id AND rt.run_id=:topic_run_id
            JOIN review_topic_results tr ON tr.review_id=rt.review_id AND tr.run_id=rt.run_id
            WHERE rt.topic=:topic AND tr.status='completed' ORDER BY fc.review_id LIMIT 20""",topic_run_id=run_id,topic=topic)]
        if not ids: return []
        params={f'example_{i}':value for i,value in enumerate(ids)}
        rows=list(self.query('SELECT * FROM filtered_reviews WHERE review_id IN ('+','.join(':'+name for name in params)+') ORDER BY review_id',**params))
        return self.review_items(rows)

    def overview(self):
        return dict(self.query((SQL_DIR / '01_overview.sql').read_text()).fetchone())

    def categories(self):
        return [dict(row) for row in self.query((SQL_DIR / '02_categories.sql').read_text())]

    def ratings(self):
        bins = {row['rating']: row['reviews'] for row in self.query(
            'SELECT rating, COUNT(*) reviews FROM filtered_reviews WHERE rating BETWEEN 1 AND 5 GROUP BY rating')}
        total = self.query('SELECT COUNT(*) FROM filtered_reviews').fetchone()[0]
        valid = sum(bins.values())
        return {'distribution': [{'rating': rating, 'reviews': bins.get(rating, 0)} for rating in range(1, 6)],
                'valid_rating_count': valid, 'invalid_or_missing_rating_count': total - valid}

    def reviews(self, page, page_size):
        meta = self.meta()
        total = meta['matched_review_count']
        offset = (page - 1) * page_size
        # Avoid SQLite int64 overflow for valid but extremely large page numbers.
        rows = list(self.query('SELECT * FROM filtered_reviews ORDER BY review_id ASC LIMIT :limit OFFSET :offset',
                              limit=page_size, offset=offset)) if offset < total else []
        return {'items': self.review_items(rows), 'page': page, 'page_size': page_size, 'total': total,
                'total_pages': (total + page_size - 1) // page_size, 'meta': meta}

    def review_items(self, rows):
        topics = {}
        if rows and self.topic_run:
            placeholders = ','.join('?' for _ in rows)
            found = self.connection.execute(f"""SELECT t.review_id,t.topic FROM review_topics t
                JOIN review_topic_results result USING (review_id,run_id)
                WHERE t.run_id=? AND result.status='completed' AND t.review_id IN ({placeholders})
                ORDER BY t.topic""", [self.topic_run['run_id']] + [row['review_id'] for row in rows])
            for row in found:
                topics.setdefault(row['review_id'], []).append(row['topic'])
        columns = ('review_id', 'clothing_id', 'title', 'review_text', 'rating', 'recommended_ind',
                   'positive_feedback_count', 'division_name', 'department_name', 'class_name',
                   'sentiment', 'sentiment_score')
        items = []
        for row in rows:
            item = {column: row[column] for column in columns}
            for column in ('title', 'review_text'):
                item[column] = mask_text(item[column])
            for column in ('division_name', 'department_name', 'class_name'):
                item[column] = item[column] or 'Unknown'
            item['complaint_topics'] = topics.get(row['review_id'], [])
            items.append(item)
        return items

    def quality(self):
        counts = dict(self.query("""SELECT COUNT(*) review_count,
            COUNT(*)-COUNT(review_text_clean) missing_text_count,
            COUNT(CASE WHEN title IS NULL OR TRIM(title, ' ' || CHAR(9) || CHAR(10) || CHAR(13))=''
                THEN 1 END) missing_title_count,
            COUNT(*)-COUNT(rating) invalid_or_missing_rating_count,
            COUNT(*)-COUNT(recommended_ind) invalid_or_missing_recommendation_count,
            COUNT(*)-COUNT(age) invalid_or_missing_age_count,
            COUNT(*)-COUNT(division_name) missing_division_count,
            COUNT(*)-COUNT(department_name) missing_department_count,
            COUNT(*)-COUNT(class_name) missing_class_count FROM filtered_reviews""").fetchone())
        report = json.loads(self.state['quality_report_json'])
        report['file'] = Path(report['file']).name
        return {'import_report': report, 'imported_at': self.state['imported_at'], 'filtered_quality': counts}

    def options(self):
        departments = [row[0] for row in self.connection.execute(
            "SELECT DISTINCT COALESCE(department_name,'Unknown') department FROM reviews ORDER BY department")]
        params = {}
        where = ''
        if self.filters.department is not None:
            where = "WHERE COALESCE(department_name,'Unknown')=:department"
            params['department'] = self.filters.department
        classes = [row[0] for row in self.connection.execute(
            "SELECT DISTINCT COALESCE(class_name,'Unknown') class FROM reviews " + where + ' ORDER BY class', params)]
        return {'departments': departments, 'classes': classes, 'ratings': [1,2,3,4,5],
                'sentiments': ['positive','neutral','negative','unknown']}

    def priorities(self):
        products = [dict(row) for row in self.query("""SELECT clothing_id,COUNT(*) reviews,
            COUNT(rating) valid_rating_count, ROUND(AVG(rating),2) avg_rating,
            SUM(CASE WHEN rating<=2 THEN 1 ELSE 0 END) low_rating_count,
            ROUND(100.0*SUM(CASE WHEN rating<=2 THEN 1 ELSE 0 END)/COUNT(rating),2) low_rating_rate_pct
            FROM filtered_reviews WHERE clothing_id IS NOT NULL GROUP BY clothing_id
            HAVING COUNT(rating)>=10 AND SUM(CASE WHEN rating<=2 THEN 1 ELSE 0 END)>0
            ORDER BY low_rating_rate_pct DESC,low_rating_count DESC,reviews DESC,clothing_id LIMIT 10""")]
        for product in products:
            product['topics'] = [dict(row) for row in self.query("""SELECT rt.topic,COUNT(DISTINCT f.review_id) mentions
                FROM filtered_reviews f JOIN review_topics rt ON rt.review_id=f.review_id AND rt.run_id=:topic_run
                JOIN review_topic_results tr ON tr.review_id=rt.review_id AND tr.run_id=rt.run_id AND tr.status='completed'
                WHERE clothing_id=:product GROUP BY rt.topic ORDER BY mentions DESC,rt.topic""",
                topic_run=self.topic_run['run_id'] if self.topic_run else None,product=product['clothing_id'])]
        condition="((rating<=2 AND sentiment='positive') OR (rating>=4 AND sentiment='negative'))"
        count=self.query('SELECT COUNT(*) FROM filtered_reviews WHERE '+condition).fetchone()[0]
        denominator=self.query("SELECT COUNT(*) FROM filtered_reviews WHERE rating IS NOT NULL AND sentiment IN ('positive','neutral','negative')").fetchone()[0]
        examples=self.review_items(list(self.query('SELECT * FROM filtered_reviews WHERE '+condition+' ORDER BY review_id LIMIT 20')))
        return {'minimum_product_ratings':10,'products':products,'disagreement_count':count,
                'compared_count':denominator,'disagreement_examples':examples}
