"""
ORBIT Agentic Dashboard DAG (Assignment 5)
Runs agentic workflow for all Forbes AI 50 companies
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
PROJECT_ROOT = Path("/opt/airflow")
sys.path.insert(0, str(PROJECT_ROOT))

from src.workflows.due_diligence_graph import run_workflow

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
    schedule_interval='0 4 * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['orbit', 'agentic', 'assignment5'],
)

# ============================================================================
# Task Functions
# ============================================================================

def get_company_list(**context):
    """Task 1: Load list of companies from payloads folder"""
    print("\n" + "="*60)
    print("TASK 1: LOADING COMPANY LIST")
    print("="*60 + "\n")
    
    data_dir = Path("/opt/airflow/data/payloads")
    
    print(f"Scanning: {data_dir}")
    print(f"Directory exists: {data_dir.exists()}")
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Payloads directory not found: {data_dir}")
    
    # Get all JSON files
    all_files = list(data_dir.glob("*.json"))
    print(f"Total JSON files: {len(all_files)}")
    
    # Filter out non-company files
    exclude_patterns = ['report', 'metadata', 'summary', 'results', 'seed']
    company_files = [f for f in all_files if not any(pattern in f.name.lower() for pattern in exclude_patterns)]
    
    print(f"Company files: {len(company_files)}")
    
    if not company_files:
        raise FileNotFoundError(f"No company JSON files found in {data_dir}")
    
    # Extract company IDs (files are named: anthropic.json, openai.json, etc.)
    company_ids = [f.stem.replace('_payload', '') for f in company_files]
    company_ids = sorted(company_ids)
    
    print(f"\n✅ Found {len(company_ids)} companies")
    print(f"   First 10: {', '.join(company_ids[:10])}")
    print(f"   Last 5: {', '.join(company_ids[-5:])}")
    
    # Push to XCom
    context['task_instance'].xcom_push(key='company_ids', value=company_ids)
    
    return f"Found {len(company_ids)} companies"


def run_agentic_workflow_for_all(**context):
    """Task 2: Run agentic workflow for each company"""
    print("\n" + "="*60)
    print("TASK 2: RUNNING AGENTIC WORKFLOWS")
    print("="*60 + "\n")
    
    # Get company list from previous task
    ti = context['task_instance']
    company_ids = ti.xcom_pull(task_ids='get_company_list', key='company_ids')
    
    if not company_ids:
        raise ValueError("No companies found in XCom!")
    
    # Set auto-approve for automated runs
    os.environ['HITL_AUTO_APPROVE'] = 'true'
    
    # Test mode: Process only first N companies (to avoid long runs during testing)
    test_limit = int(os.getenv('DAG_TEST_LIMIT', '50'))
    companies_to_process = company_ids[:test_limit]
    
    print(f"Total companies available: {len(company_ids)}")
    print(f"Processing (TEST MODE): {len(companies_to_process)} companies")
    print(f"   Set DAG_TEST_LIMIT=52 to process all companies")
    print(f"   Companies: {', '.join(companies_to_process)}\n")
    
    # Track results
    results = {
        'total_available': len(company_ids),
        'total_processed': len(companies_to_process),
        'successful': 0,
        'failed': 0,
        'hitl_triggered': 0,
        'companies': []
    }
    
    # Run workflow for each company
    for idx, company_id in enumerate(companies_to_process, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(companies_to_process)}] {company_id.upper()}")
        print(f"{'='*60}")
        
        try:
            # Run the agentic workflow
            final_state = run_workflow(company_id)
            
            # Record success
            results['successful'] += 1
            if final_state.get('hitl_required'):
                results['hitl_triggered'] += 1
            
            results['companies'].append({
                'company_id': company_id,
                'status': 'success',
                'risk_detected': final_state.get('risk_detected', False),
                'hitl_required': final_state.get('hitl_required', False),
                'hitl_approved': final_state.get('hitl_approved', False),
                'recommendation': 'APPROVED' if final_state.get('hitl_approved') else 'REJECTED',
                'execution_path': ' -> '.join(final_state.get('execution_path', []))
            })
            
            print(f"✅ {company_id}: SUCCESS")
            print(f"   Risk: {final_state.get('risk_detected')}")
            print(f"   Branch: {'HITL' if final_state.get('hitl_required') else 'Auto-Approve'}")
            
        except Exception as e:
            print(f"❌ {company_id}: FAILED")
            print(f"   Error: {str(e)}")
            
            import traceback
            traceback.print_exc()
            
            results['failed'] += 1
            results['companies'].append({
                'company_id': company_id,
                'status': 'failed',
                'error': str(e)[:500]  # Truncate long errors
            })
    
    # Save results summary
    results_file = Path("/opt/airflow/data/agentic_dag_results.json")
    
    with open(results_file, 'w') as f:
        json.dump({
            'dag_id': 'orbit_agentic_dashboard',
            'execution_date': context['execution_date'].isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
            'test_mode': test_limit < len(company_ids),
            'test_limit': test_limit,
            'summary': results,
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print("AGENTIC WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"Processed:      {results['total_processed']}/{results['total_available']}")
    print(f"Successful:     {results['successful']}")
    print(f"Failed:         {results['failed']}")
    print(f"HITL Triggered: {results['hitl_triggered']}")
    print(f"Success Rate:   {results['successful']/results['total_processed']*100:.1f}%")
    print(f"Results:        {results_file}")
    print(f"{'='*60}\n")
    
    return f"✅ {results['successful']}/{results['total_processed']} companies successful"


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

# ============================================================================
# Task Dependencies
# ============================================================================

task_get_companies >> task_run_workflow
