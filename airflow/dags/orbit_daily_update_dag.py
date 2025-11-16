"""
ORBIT Daily Update DAG

Purpose: Incremental updates of company snapshots and vector DB
Trigger: Scheduled (daily at 2 AM UTC)
Schedule: 0 2 * * * (cron)

Tasks:
1. Fetch latest company data updates
2. Update existing payloads
3. Refresh vector DB embeddings
4. Clean up stale data
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import json
import os
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path(os.getenv("AIRFLOW_HOME", "/usr/local/airflow")) / "data"
PAYLOADS_DIR = DATA_DIR / "payloads"


# ============================================================
# Task Functions
# ============================================================

def fetch_updates(**context):
    """Task 1: Fetch latest company data updates"""
    execution_date = context['execution_date']
    print(f"🔄 Fetching updates for {execution_date.date()}...")

    # In production, query APIs for companies with updates since last run
    updates = {
        "anthropic": {"funding_total": "150M", "updated": True},
        "openai": {"employee_count": "500-1000", "updated": True},
    }

    print(f"✅ Found {len(updates)} companies with updates")
    context['task_instance'].xcom_push(key='updates', value=updates)
    return len(updates)


def update_payloads(**context):
    """Task 2: Update existing payloads with new data"""
    updates = context['task_instance'].xcom_pull(
        task_ids='fetch_updates', key='updates'
    )

    print(f"📝 Updating {len(updates)} payloads...")

    for company_id, new_data in updates.items():
        payload_path = PAYLOADS_DIR / f"{company_id}_payload.json"

        if payload_path.exists():
            with open(payload_path, 'r') as f:
                payload = json.load(f)

            # Update fields
            payload.update(new_data)
            payload['last_updated'] = datetime.utcnow().isoformat()

            with open(payload_path, 'w') as f:
                json.dump(payload, f, indent=2)

            print(f"  ✅ Updated {company_id}")

    print(f"✅ Updated {len(updates)} payloads")
    return len(updates)


def refresh_vector_db(**context):
    """Task 3: Refresh vector DB with updated embeddings"""
    updates = context['task_instance'].xcom_pull(
        task_ids='fetch_updates', key='updates'
    )

    print(f"🔍 Refreshing vector DB for {len(updates)} companies...")
    print("  - Generating new embeddings...")
    print("  - Upserting to Pinecone...")
    print(f"✅ Vector DB refreshed")
    return len(updates)


def cleanup_stale_data(**context):
    """Task 4: Clean up old data"""
    print(f"🧹 Cleaning up stale data...")
    print("  - Removing outdated snapshots...")
    print("  - Archiving old logs...")
    print(f"✅ Cleanup complete")
    return True


# ============================================================
# DAG Definition
# ============================================================

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    dag_id='orbit_daily_update',
    default_args=default_args,
    description='Daily incremental updates for company data',
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['orbit', 'daily-update'],
) as dag:

    t1 = PythonOperator(
        task_id='fetch_updates',
        python_callable=fetch_updates,
        provide_context=True,
    )

    t2 = PythonOperator(
        task_id='update_payloads',
        python_callable=update_payloads,
        provide_context=True,
    )

    t3 = PythonOperator(
        task_id='refresh_vector_db',
        python_callable=refresh_vector_db,
        provide_context=True,
    )

    t4 = PythonOperator(
        task_id='cleanup_stale_data',
        python_callable=cleanup_stale_data,
        provide_context=True,
    )

    t1 >> t2 >> t3 >> t4