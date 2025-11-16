"""
ORBIT Agentic Dashboard DAG

Purpose: Invokes MCP Server + Agentic Workflow to generate PE dashboards
Trigger: Scheduled (daily at 3 AM UTC, after daily_update completes)
Schedule: 0 3 * * * (cron)

Tasks:
1. Check MCP Server health
2. Get Forbes AI 50 company list
3. Run due diligence workflow for each company
4. Collect and store dashboards
5. Generate summary report
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import json
import os
import sys
from pathlib import Path
import subprocess


# ============================================================
# Configuration
# ============================================================

MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:9000")
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = Path(os.getenv("AIRFLOW_HOME", "/usr/local/airflow")) / "data"
DASHBOARDS_DIR = DATA_DIR / "dashboards"


# ============================================================
# Task Functions
# ============================================================

def check_mcp_health(**context):
    """Task 1: Check MCP Server health before starting"""
    import requests

    print(f"🏥 Checking MCP Server health at {MCP_BASE_URL}...")

    try:
        response = requests.get(f"{MCP_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ MCP Server is healthy: {health_data}")
            return True
        else:
            raise Exception(f"MCP Server unhealthy: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ MCP Server health check failed: {e}")
        raise


def get_company_list(**context):
    """Task 2: Get Forbes AI 50 company list from MCP Server"""
    import requests

    print(f"📋 Fetching company list from MCP Server...")

    try:
        response = requests.get(f"{MCP_BASE_URL}/resource/ai50/companies", timeout=10)
        if response.status_code == 200:
            data = response.json()
            companies = data.get("companies", [])
            print(f"✅ Retrieved {len(companies)} companies")

            # For demo, limit to first 5 companies to avoid long execution
            companies = companies[:5]
            print(f"   Processing {len(companies)} companies for this run")

            context['task_instance'].xcom_push(key='companies', value=companies)
            return len(companies)
        else:
            raise Exception(f"Failed to fetch companies: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching company list: {e}")
        # Fallback to hardcoded list
        fallback = ["anthropic", "openai", "cohere"]
        context['task_instance'].xcom_push(key='companies', value=fallback)
        return len(fallback)


def run_agentic_workflow(**context):
    """
    Task 3: Run due diligence workflow for each company
    Invokes the LangGraph workflow via CLI
    """
    companies = context['task_instance'].xcom_pull(
        task_ids='get_company_list', key='companies'
    )

    print(f"🤖 Running agentic workflow for {len(companies)} companies...")

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for idx, company_id in enumerate(companies, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(companies)}] Processing {company_id}...")
        print('='*60)

        try:
            # Run workflow using subprocess
            env = os.environ.copy()
            env['PYTHONPATH'] = str(PROJECT_ROOT)
            env['HITL_AUTO_APPROVE'] = 'true'  # Auto-approve for scheduled runs

            workflow_script = PROJECT_ROOT / "src" / "workflows" / "due_diligence_graph.py"

            result = subprocess.run(
                [sys.executable, str(workflow_script), company_id],
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per company
            )

            if result.returncode == 0:
                print(f"✅ Workflow completed for {company_id}")
                results.append({
                    "company_id": company_id,
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                print(f"❌ Workflow failed for {company_id}")
                print(f"Error: {result.stderr}")
                results.append({
                    "company_id": company_id,
                    "status": "failed",
                    "error": result.stderr[:500],
                    "timestamp": datetime.utcnow().isoformat()
                })

        except subprocess.TimeoutExpired:
            print(f"⏱️  Workflow timeout for {company_id}")
            results.append({
                "company_id": company_id,
                "status": "timeout",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ Unexpected error for {company_id}: {e}")
            results.append({
                "company_id": company_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    # Save results
    results_path = DASHBOARDS_DIR / f"workflow_results_{context['ds']}.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Completed workflows for {len(companies)} companies")
    print(f"   Successes: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"   Failures: {sum(1 for r in results if r['status'] in ['failed', 'timeout', 'error'])}")

    context['task_instance'].xcom_push(key='results', value=results)

    return len(results)


def generate_summary_report(**context):
    """Task 4: Generate summary report of all dashboards"""
    results = context['task_instance'].xcom_pull(
        task_ids='run_agentic_workflow', key='results'
    )

    print(f"📊 Generating summary report...")

    summary = {
        "execution_date": context['ds'],
        "total_companies": len(results),
        "successful": sum(1 for r in results if r['status'] == 'success'),
        "failed": sum(1 for r in results if r['status'] != 'success'),
        "results": results,
        "generated_at": datetime.utcnow().isoformat()
    }

    # Save summary report
    report_path = DASHBOARDS_DIR / f"summary_report_{context['ds']}.json"
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Summary report saved to {report_path}")
    print(f"\n📈 SUMMARY:")
    print(f"   Total Companies: {summary['total_companies']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Failed: {summary['failed']}")

    return summary


# ============================================================
# DAG Definition
# ============================================================

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_success': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=15),
}

with DAG(
    dag_id='orbit_agentic_dashboard',
    default_args=default_args,
    description='Generate PE dashboards using MCP + Agentic Workflow',
    schedule_interval='0 3 * * *',  # Daily at 3 AM UTC (after daily_update)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['orbit', 'agentic', 'dashboards'],
) as dag:

    t1_health = PythonOperator(
        task_id='check_mcp_health',
        python_callable=check_mcp_health,
        provide_context=True,
    )

    t2_companies = PythonOperator(
        task_id='get_company_list',
        python_callable=get_company_list,
        provide_context=True,
    )

    t3_workflow = PythonOperator(
        task_id='run_agentic_workflow',
        python_callable=run_agentic_workflow,
        provide_context=True,
        execution_timeout=timedelta(hours=2),  # Max 2 hours for all workflows
    )

    t4_summary = PythonOperator(
        task_id='generate_summary_report',
        python_callable=generate_summary_report,
        provide_context=True,
    )

    # Task dependencies
    t1_health >> t2_companies >> t3_workflow >> t4_summary


# ============================================================
# Documentation
# ============================================================

"""
How to Run:
-----------

1. Manual trigger:
   ```bash
   airflow dags trigger orbit_agentic_dashboard
   ```

2. Check status:
   ```bash
   airflow dags state orbit_agentic_dashboard <execution_date>
   ```

3. View logs:
   ```bash
   airflow tasks logs orbit_agentic_dashboard run_agentic_workflow <execution_date>
   ```

4. Check results:
   ```bash
   cat /usr/local/airflow/data/dashboards/summary_report_<date>.json
   ```

Expected Behavior:
------------------
- Runs daily at 3 AM UTC (after daily_update completes)
- Processes all Forbes AI 50 companies (or subset for testing)
- Each company runs through full LangGraph workflow
- HITL auto-approves (no manual intervention needed)
- Results saved to data/dashboards/
- Summary report generated

Duration: ~30-60 minutes (depends on number of companies)
"""