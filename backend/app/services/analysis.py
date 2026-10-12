"""Resumable analysis caches and atomic selected-run promotion."""
import hashlib
import json
import random
from datetime import datetime,timezone
from pathlib import Path
from time import monotonic

from backend.app.db import connect
from .topics import TAXONOMY_VERSION,classify_topics,has_explicit_complaint

def now(): return datetime.now(timezone.utc).isoformat()

def guard(connection, checksum):
    state=connection.execute('SELECT * FROM import_state WHERE id=1').fetchone()
    if state is None or state['dataset_sha256'] != checksum:
        raise ValueError('Dataset changed during analysis; rerun against current import')
    return state

def run_analysis(database, kind, *, predict=None, model_id=None, revision=None, limit=None, batch_size=16, seed=20261012, report_dir=None):
    started=monotonic()
    with connect(database,readonly=True) as c:
        state=c.execute('SELECT * FROM import_state WHERE id=1').fetchone()
        if state is None: raise ValueError('Import dataset first')
        checksum=state['dataset_sha256']; source=None
        if kind=='sentiment':
            rows=[dict(r) for r in c.execute('SELECT review_id,review_text_clean FROM reviews WHERE review_text_clean IS NOT NULL ORDER BY review_id')]
        elif kind=='topics':
            source=state['selected_sentiment_run_id']
            if source:
                run=c.execute("SELECT 1 FROM analysis_runs WHERE run_id=? AND kind='sentiment' AND status='completed' AND dataset_sha256=?",(source,checksum)).fetchone()
                if run is None: raise ValueError('Select a compatible completed sentiment run first')
            c.create_function('topic_concern',1,has_explicit_complaint,deterministic=True)
            rows=[dict(r) for r in c.execute("""SELECT r.review_id,r.review_text_clean FROM reviews r
                LEFT JOIN review_predictions p ON p.review_id=r.review_id AND p.run_id=?
                WHERE r.review_text_clean IS NOT NULL AND (r.rating<=2 OR p.sentiment='negative' OR topic_concern(r.review_text_clean)=1) ORDER BY r.review_id""",(source,))]
        else: raise ValueError('Invalid analysis kind')
    eligible=len(rows)
    if limit is not None and limit<len(rows): rows=sorted(random.Random(seed).sample(rows,limit),key=lambda r:r['review_id'])
    method='transformers' if kind=='sentiment' else 'keyword_baseline'
    if kind=='sentiment' and (not revision or len(revision)!=40): raise ValueError('Immutable 40-character model revision required')
    config={'kind':kind,'checksum':checksum,'model_id':model_id,'revision':revision,'taxonomy':TAXONOMY_VERSION if kind=='topics' else None,'source':source,'limit':limit,'seed':seed,'max_length':256 if kind=='sentiment' else None}
    run_id=kind+'-'+hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:24]
    table='review_predictions' if kind=='sentiment' else 'review_topic_results'
    selected_column='selected_sentiment_run_id' if kind=='sentiment' else 'selected_topic_run_id'
    with connect(database) as c:
        c.execute('BEGIN IMMEDIATE');guard(c,checksum)
        c.execute("""INSERT OR IGNORE INTO analysis_runs
            (run_id,kind,method,model_id,model_revision,taxonomy_version,dataset_sha256,source_sentiment_run_id,started_at,status,eligible_count,processed_count)
            VALUES (?,?,?,?,?,?,?,?,?,'running',?,0)""",(run_id,kind,method,model_id,revision,config['taxonomy'],checksum,source,now(),eligible))
        done={row[0] for row in c.execute(f'SELECT review_id FROM {table} WHERE run_id=?',(run_id,))}
        pending=[row for row in rows if row['review_id'] not in done]
        cached_complete=not pending and c.execute('SELECT status FROM analysis_runs WHERE run_id=?',(run_id,)).fetchone()[0]=='completed'
        # A completed cache remains visible to readers while it is reused/promoted.
        if not cached_complete:
            c.execute("UPDATE analysis_runs SET status='running',completed_at=NULL WHERE run_id=?",(run_id,))
        c.commit()
    try:
        for index in range(0,len(pending),batch_size):
            batch=pending[index:index+batch_size]
            results=predict([row['review_text_clean'] for row in batch]) if kind=='sentiment' else [classify_topics(row['review_text_clean']) for row in batch]
            if len(results)!=len(batch): raise ValueError('Prediction count mismatch')
            with connect(database) as c:
                c.execute('BEGIN IMMEDIATE'); current=guard(c,checksum)
                if kind=='topics' and current['selected_sentiment_run_id']!=source: raise ValueError('Selected sentiment run changed during topic analysis')
                for row,result in zip(batch,results):
                    if kind=='sentiment':
                        label,score=result
                        if label not in ('positive','neutral','negative') or not 0<=score<=1: raise ValueError('Invalid prediction')
                        c.execute('INSERT INTO review_predictions VALUES (?,?,?,?)',(row['review_id'],run_id,label,score))
                    else:
                        c.execute("INSERT INTO review_topic_results VALUES (?,?,'completed')",(row['review_id'],run_id))
                        c.executemany('INSERT INTO review_topics VALUES (?,?,?)',[(row['review_id'],run_id,topic) for topic in result])
                count=c.execute(f'SELECT COUNT(*) FROM {table} WHERE run_id=?',(run_id,)).fetchone()[0]
                c.execute('UPDATE analysis_runs SET processed_count=? WHERE run_id=?',(count,run_id));c.commit()
            if index//batch_size%20==0: print(f'{kind}: {count}/{len(rows)} target, {eligible} eligible',flush=True)
        with connect(database) as c:
            c.execute('BEGIN IMMEDIATE');current=guard(c,checksum)
            if kind=='topics' and current['selected_sentiment_run_id']!=source: raise ValueError('Selected sentiment run changed before promotion')
            if not cached_complete:
                c.execute("UPDATE analysis_runs SET status='completed',completed_at=? WHERE run_id=?",(now(),run_id))
            if kind=='sentiment' and current['selected_sentiment_run_id']!=run_id:
                c.execute('UPDATE import_state SET selected_topic_run_id=NULL WHERE id=1')
            c.execute(f'UPDATE import_state SET {selected_column}=? WHERE id=1',(run_id,));c.commit()
    except BaseException:
        if not cached_complete:
            with connect(database) as c:
                c.execute("UPDATE analysis_runs SET status='failed' WHERE run_id=?",(run_id,));c.commit()
        raise
    report=config|{'run_id':run_id,'method':method,'eligible_count':eligible,'processed_count':len(rows),'cached_count':len(done),'elapsed_seconds':round(monotonic()-started,2),'selection':'all' if len(rows)==eligible else f'deterministic random sample; seed={seed}'}
    if report_dir:
        Path(report_dir).mkdir(parents=True,exist_ok=True)
        (Path(report_dir)/f'{run_id}.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
