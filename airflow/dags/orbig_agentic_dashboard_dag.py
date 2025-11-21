"""
ORBIT Agentic Dashboard DAG (Assignment 5)
Runs agentic workflow for all Forbes AI 50 companies

Invokes MCP + Agent Workflow to:
1. Load structured payloads
2. Generate dashboards via agentic workflow
3. Detect risks and trigger HITL if needed
4. Save final dashboards
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
from pathlib import Path
import json
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.workflows.due_diligence_graph import run_workflow
from src.utils import ScraperConfig, load_json

# ============================================================================
# DAG Configuration
# ============================================================================

default_args = {
    'owner': 'orbit',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='orbit_agentic_dashboard',
    default_args=default_args,
    description='Generate dashboards using agentic workflow for all AI 50 companies',
    schedule_interval='0 4 * * *',  # Run daily at 4 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['orbit', 'agentic', 'assignment5'],
)

# ============================================================================
# Task Functions
# ============================================================================

def get_company_list(**context):
    """
    Task 1: Load list of companies from payloads folder
    """
    print("\n" + "="*60)
    print("TASK 1: LOADING COMPANY LIST")
    print("="*60 + "\n")
    
    # Load from payloads directory (your Assignment 4 output)
    payloads_dir = ScraperConfig.DATA_DIR / "payloads"
    
    if not payloads_dir.exists():
        # Fallback to structured directory if payloads doesn't exist
        payloads_dir = ScraperConfig.DATA_DIR / "structured"
    
    company_files = list(payloads_dir.glob("*_payload.json")) or list(payloads_dir.glob("*.json"))
    
    # Extract company IDs
    company_ids = []
    for file in company_files:
        # Handle both formats: anthropic_payload.json or anthropic.json
        company_id = file.stem.replace('_payload', '')
        company_ids.append(company_id)
    
    print(f"Found {len(company_ids)} companies in {payloads_dir}")
    print(f"Companies: {', '.join(company_ids[:5])}...")
    
    # Push to XCom for next task
    context['task_instance'].xcom_push(key='company_ids', value=company_ids)
    
    return f"Found {len(company_ids)} companies"


def run_agentic_workflow_for_all(**context):
    """
    Task 2: Run agentic workflow for each company
    
    This runs your LangGraph workflow (due_diligence_graph.py) which:
    - Calls MCP server to generate dashboards
    - Evaluates them
    - Detects risks
    - Triggers HITL if needed
    - Saves final dashboards
    """
    print("\n" + "="*60)
    print("TASK 2: RUNNING AGENTIC WORKFLOWS")
    print("="*60 + "\n")
    
    # Get company list from previous task
    ti = context['task_instance']
    company_ids = ti.xcom_pull(task_ids='get_company_list', key='company_ids')
    
    if not company_ids:
        print("No companies found!")
        return "No companies processed"
    
    # Set auto-approve mode for Airflow (no interactive HITL)
    os.environ['HITL_AUTO_APPROVE'] = 'true'
    
    # Track results
    results = {
        'total': len(company_ids),
        'successful': 0,
        'failed': 0,
        'hitl_triggered': 0,
        'companies': []
    }
    
    # Run workflow for each company
    for idx, company_id in enumerate(company_ids, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(company_ids)}] Processing: {company_id}")
        print(f"{'='*60}")
        
        try:
            # Run the workflow (from due_diligence_graph.py)
            # This will:
            # 1. Call MCP server to generate dashboards
            # 2. Evaluate and detect risks
            # 3. Save dashboards to data/dashboards/
            final_state = run_workflow(company_id)
            
            # Track results
            company_result = {
                'company_id': company_id,
                'status': 'success',
                'risk_detected': final_state.get('risk_detected', False),
                'hitl_required': final_state.get('hitl_required', False),
                'recommendation': final_state.get('final_decision', {}).get('recommendation'),
                'execution_path': final_state.get('execution_path', [])
            }
            
            results['successful'] += 1
            if final_state.get('hitl_required'):
                results['hitl_triggered'] += 1
            
            results['companies'].append(company_result)
            
            print(f"✅ {company_id}: SUCCESS")
            print(f"   Risk detected: {final_state.get('risk_detected')}")
            print(f"   Branch: {'HITL' if final_state.get('hitl_required') else 'Auto-Approve'}")
            
        except Exception as e:
            print(f"❌ {company_id}: FAILED - {str(e)}")
            
            results['failed'] += 1
            results['companies'].append({
                'company_id': company_id,
                'status': 'failed',
                'error': str(e)
            })
    
    # Save results summary
    results_file = ScraperConfig.DATA_DIR / "agentic_dag_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'execution_date': context['execution_date'].isoformat(),
            'results': results
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print("AGENTIC WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"Total: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"HITL triggered: {results['hitl_triggered']}")
    print(f"Results saved: {results_file}")
    print(f"{'='*60}\n")
    
    # Push summary to XCom
    context['task_instance'].xcom_push(key='results', value=results)
    
    return f"Processed {results['successful']}/{results['total']} companies"


def cleanup_old_dashboards(**context):
    """
    Task 3: Optional cleanup of old dashboard files
    Keeps only the latest 5 dashboards per company
    """
    print("\n" + "="*60)
    print("TASK 3: CLEANING UP OLD DASHBOARDS")
    print("="*60 + "\n")
    
    dashboards_dir = ScraperConfig.DATA_DIR / "dashboards"
    
    if not dashboards_dir.exists():
        print("No dashboards directory found")
        return "No cleanup needed"
    
    cleaned = 0
    
    for company_dir in dashboards_dir.iterdir():
        if not company_dir.is_dir():
            continue
        
        # Get all dashboard files sorted by timestamp
        dashboard_files = sorted(
            company_dir.glob("structured_*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Keep only latest 5, delete rest
        for old_file in dashboard_files[5:]:
            old_file.unlink()
            cleaned += 1
            print(f"Deleted: {old_file}")
    
    print(f"\nCleaned up {cleaned} old dashboard files")
    
    return f"Cleaned {cleaned} files"


# ============================================================================
# Define Tasks
# ============================================================================

task_get_companies = PythonOperator(
    task_id='get_company_list',
    python_callable=get_company_list,
    dag=dag,
)

task_run_workflow = PythonOperator(
    task_id='run_agentic_workflow',
    python_callable=run_agentic_workflow_for_all,
    dag=dag,
)

task_cleanup = PythonOperator(
    task_id='cleanup_old_dashboards',
    python_callable=cleanup_old_dashboards,
    dag=dag,
)

# ============================================================================
# Task Dependencies
# ============================================================================

task_get_companies >> task_run_workflow >> task_cleanup