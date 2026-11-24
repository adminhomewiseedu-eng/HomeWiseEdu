"""Synthetic PostgreSQL 18 + real process checks. Never reads production configuration.

Uses existing Windows tools; creates a fresh localhost-only cluster, runs the exact
0014 fixture through real Alembic, tests three databases, then stops the cluster.
It does not run the historical clean-bootstrap chain or access encrypted backups.
"""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def main():
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    tools=Path(r'C:\Program Files\PostgreSQL\18\bin')
    assert (tools/'pg_ctl.exe').is_file(),'PostgreSQL 18 Windows tools required'
    workspace=Path(tempfile.mkdtemp(prefix='hwe-recovery-local-')).resolve()
    port=free_port();password=secrets.token_urlsafe(32);admin='recovery_local_qa'
    for key in list(os.environ):
        if key.startswith(('PG','RAILWAY_')):del os.environ[key]
    os.environ.update(ENVIRONMENT='test',AUTO_INIT_DB='false',SEED_MODE='none',
        DATABASE_URL='sqlite://',STORAGE_ROOT=str(workspace/'uploads'),TTS_CACHE_DIR=str(workspace/'audio'),
        OPENAI_API_KEY='',ELEVENLABS_API_KEY='',RESEND_API_KEY='',SMTP_HOST='')
    (workspace/'uploads').mkdir();(workspace/'audio').mkdir()
    env=os.environ.copy();env.update(TEMP=str(workspace),TMP=str(workspace))
    def native(exe,args,timeout=60,check=True):
        with (workspace/(exe+'.log')).open('ab') as log:
            return subprocess.run([str(tools/(exe+'.exe')),*map(str,args)],env=env,
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=timeout,check=check)
    started=False
    try:
        pw=workspace/'local-init-password';pw.write_text(password,encoding='utf-8')
        native('initdb',['-D',workspace/'data','-U',admin,'--pwfile='+str(pw),'--auth=scram-sha-256','--encoding=UTF8','--locale=C'])
        pw.unlink()
        started=True
        native('pg_ctl',['-D',workspace/'data','-l',workspace/'postgres.log','-o',f'-h 127.0.0.1 -p {port}','-w','-t','30','start'],45)
        import psycopg
        import sqlalchemy as sa
        from alembic import command
        from alembic.config import Config
        from unittest.mock import patch
        from backend.config import settings
        from backend.tests.test_recovery_schema import exercise_recovery, history_snapshot
        migration_dir=workspace/'migrations';versions=migration_dir/'versions';versions.mkdir(parents=True)
        shutil.copyfile(root/'backend/migrations/env.py',migration_dir/'env.py')
        shutil.copyfile(root/'backend/tests/fixtures/0014_lesson_assignments.py',versions/'0014_lesson_assignments.py')
        (versions/'0013_existing.py').write_text("revision='0013_programme_entitlements'\ndown_revision=None\ndef upgrade():\n raise RuntimeError('Do not bootstrap history')\ndef downgrade():\n raise RuntimeError('No historical downgrade')\n",encoding='utf-8')
        def migrate(engine):
            config=Config(str(root/'alembic.ini'));config.set_main_option('script_location',str(migration_dir))
            with patch.object(settings,'DATABASE_URL',engine.url.render_as_string(hide_password=False)):
                command.upgrade(config,'0014_lesson_assignments')
        results=[]
        for revision,populated in [('0013',False),('0014',False),('0014',True)]:
            dbname='recovery_'+revision+('_populated' if populated else '_empty')
            with psycopg.connect(host='127.0.0.1',port=port,dbname='postgres',user=admin,password=password,autocommit=True) as c:
                c.execute(sa.text('SELECT 1').text)
                c.execute('CREATE DATABASE '+dbname)
            url=sa.URL.create('postgresql+psycopg',username=admin,password=password,host='127.0.0.1',port=port,database=dbname)
            engine=sa.create_engine(url)
            try:
                result=exercise_recovery(engine,revision,populated,migrate=migrate)
                before=history_snapshot(engine,populated)
                result['real_process']=verify_process(root,workspace,env,url.render_as_string(hide_password=False))
                assert history_snapshot(engine,populated)==before,'Startup or real HTTP requests changed protected data'
                results.append(result);print(json.dumps(result),flush=True)
            finally:engine.dispose()
        (workspace/'verification-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print('PostgreSQL 18 recovery compatibility: PASS',flush=True)
    finally:
        if started:
            result=native('pg_ctl',['-D',workspace/'data','-w','-t','30','-m','fast','stop'],45,False)
            if result.returncode!=0:native('pg_ctl',['-D',workspace/'data','-w','-t','15','-m','immediate','stop'],25,False)
            if native('pg_ctl',['-D',workspace/'data','status'],15,False).returncode!=3:
                raise RuntimeError('Disposable PostgreSQL shutdown unconfirmed')
            print('Disposable PostgreSQL stopped; synthetic artifacts:',workspace,flush=True)


def verify_process(root,workspace,base_env,url):
    """Real production-mode uvicorn import/startup, no app seeding or live API keys."""
    import httpx
    port=free_port()
    env=base_env.copy()
    env.update(ENVIRONMENT='production',DATABASE_URL=url,AUTO_INIT_DB='false',SEED_MODE='none',
        SECRET_KEY='local-recovery-only-secret-not-production-000000000000',
        OPENAI_API_KEY='local-placeholder-no-external-requests',ELEVENLABS_API_KEY='local-placeholder',
        ELEVENLABS_VOICE_ID='local-placeholder',ALLOWED_ORIGINS='https://local.example.test',
        FRONTEND_URL='https://local.example.test',SMTP_HOST='local.invalid',SMTP_FROM_EMAIL='support@example.test')
    path=workspace/('uvicorn-'+str(port)+'.log')
    with path.open('xb') as log:
        proc=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(port)],
                              cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=4,trust_env=False) as client:
                while True:
                    if proc.poll() is not None:raise RuntimeError('Production-mode local startup failed')
                    try:
                        response=client.get('/ready')
                        if response.status_code==200:break
                    except httpx.HTTPError:pass
                    if time.monotonic()>deadline:raise RuntimeError('Production-mode readiness timed out')
                    time.sleep(.3)
                assert client.get('/health').status_code==200
                for programme in ('homeschool','bible_study'):
                    for role in ('parent','student'):
                        response=client.post('/api/auth/login',json={'email':f'{programme}-{role}@example.test','password':'DisposableRecovery123!'})
                        assert response.status_code==200
                        assert response.json()['user']['programme']==programme
                assert client.get('/api/curriculum/subjects').status_code in (200,401)
            return 'production-mode startup, health, readiness and four real HTTP logins PASS'
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)


if __name__=='__main__':main()
