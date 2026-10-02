"""Query the BigQuery copy of the Kalshi archive into pandas.

Queries bill to the project owner's card, so every query has a hard cap on
bytes billed (BigQuery refuses to run a query that would exceed it).

    from bq import query
    df = query("SELECT ... FROM `kalshi-archive-2026.kalshi_archive.trades` WHERE created_time >= ...")
"""

from google.cloud import bigquery

PROJECT = "kalshi-archive-2026"
DATASET = f"{PROJECT}.kalshi_archive"
_client = None


def client():
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT)
    return _client


def estimate_gb(sql):
    job = client().query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    return job.total_bytes_processed / 1e9


def query(sql, max_gb=20):
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=int(max_gb * 1e9))
    job = client().query(sql, job_config=cfg)
    # Our account lacks bigquery.readsessions.create, so skip the Storage API
    # and download through the (slower) REST endpoint.
    df = job.to_dataframe(create_bqstorage_client=False)
    print(f"[bq] {job.total_bytes_billed / 1e9:.2f} GB billed, {len(df):,} rows")
    return df
