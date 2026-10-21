import os
import pathlib
import subprocess
import sys
from uuid import uuid4
import psycopg
from psycopg import sql

root=pathlib.Path('/private/tmp/offersteady-cn-model-1017-20261021')
python='/Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python'
local_admin='postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/postgres'
database='synthetic_model_1017_release_'+uuid4().hex
tests='''test_model_1017_compatibility.py
test_model_1017_probe_guards.py
test_model_1017_adapter_probe_guards.py
test_chat_answer_completeness.py
test_web_search_chat_integration.py
test_screenshot_answer_repository.py
test_screenshot_stream_admission.py
test_screenshot_inline_delivery.py
test_written_multi_screen_answer.py
test_cn_resume_optimizer_provider.py
test_cn_resume_optimizer_safe_edit_provider.py
test_cn_resume_optimizer_safe_edits.py
test_cn_resume_optimizer_provider_diagnostics.py
test_mock_interview_generation.py
test_mock_interview_readiness.py
test_mock_interview_labels.py
test_interview_usage_billing.py
test_billing_catalog.py
test_cn_resume_optimizer_billing.py
test_cn_resume_optimizer_service.py
test_mock_interview_api.py
test_mock_interview_postgres.py
test_cn_mock_flat_billing_postgres.py
test_mock_interview_rounds.py'''.splitlines()
with psycopg.connect(local_admin,autocommit=True,connect_timeout=3) as c:
    c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
try:
    env=dict(os.environ)
    env['PYTHONPATH']='apps/backend'
    env['OFFERSTEADY_TEST_DATABASE_URL']=local_admin.rsplit('/',1)[0]+'/'+database
    command=[python,'-m','pytest','-q','--tb=short']+['apps/backend/tests/'+name for name in tests]
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True)
    output=result.stdout+result.stderr
    pathlib.Path('/private/tmp/cn-model-1017-release-local-final-20261021.txt').write_text(output)
    print(output)
    code=result.returncode
finally:
    with psycopg.connect(local_admin,autocommit=True,connect_timeout=3) as c:
        c.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
raise SystemExit(code)
