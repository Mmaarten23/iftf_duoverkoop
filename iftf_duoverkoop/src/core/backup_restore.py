"""Database backup/restore helpers using PostgreSQL native tools."""
import hashlib
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import connections
from django.utils import timezone

from iftf_duoverkoop.src.core.models import DatabaseOperation

logger = logging.getLogger('iftf_duoverkoop.dbops')


def _backup_dir() -> Path:
    backup_dir = Path(getattr(settings, 'DATABASE_BACKUP_DIR', Path(settings.MEDIA_ROOT) / 'backups'))
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _split_db_config() -> tuple[dict, str]:
    db_cfg = settings.DATABASES.get('default', {})
    engine = db_cfg.get('ENGINE', '')
    if 'postgresql' not in engine:
        raise RuntimeError('Database backup/restore is only supported for PostgreSQL.')

    database_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in ('postgres', 'postgresql'):
            raise RuntimeError('DATABASE_URL is not a PostgreSQL connection string.')
        dbname = (parsed.path or '/').lstrip('/')
        env = {
            'PGHOST': parsed.hostname or '',
            'PGPORT': str(parsed.port or 5432),
            'PGUSER': parsed.username or '',
            'PGPASSWORD': parsed.password or '',
            'PGSSLMODE': os.environ.get('PGSSLMODE', 'require'),
        }
        if not dbname:
            raise RuntimeError('DATABASE_URL does not contain a database name.')
        return env, dbname

    dbname = db_cfg.get('NAME')
    if not dbname:
        raise RuntimeError('No PostgreSQL database name configured.')

    env = {
        'PGHOST': db_cfg.get('HOST', ''),
        'PGPORT': str(db_cfg.get('PORT', '') or 5432),
        'PGUSER': db_cfg.get('USER', ''),
        'PGPASSWORD': db_cfg.get('PASSWORD', ''),
        'PGSSLMODE': os.environ.get('PGSSLMODE', 'require'),
    }
    return env, str(dbname)


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _run_process(command: list[str], env_updates: dict) -> tuple[str, str]:
    env = os.environ.copy()
    env.update(env_updates)
    try:
        completed = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Required executable '{command[0]}' is not available on this host."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or '').strip()
        stdout = (exc.stdout or '').strip()
        detail = stderr or stdout or str(exc)
        raise RuntimeError(detail) from exc

    return (completed.stdout or '').strip(), (completed.stderr or '').strip()


def _set_running(job: DatabaseOperation) -> None:
    job.status = DatabaseOperation.STATUS_RUNNING
    job.started_at = timezone.now()
    job.error_message = ''
    job.save(update_fields=['status', 'started_at', 'error_message'])


def _set_failed(job: DatabaseOperation, error: str, output: str = '') -> None:
    job.status = DatabaseOperation.STATUS_FAILED
    job.finished_at = timezone.now()
    job.error_message = error[:8000]
    if output:
        job.output_log = output[:16000]
    job.save(update_fields=['status', 'finished_at', 'error_message', 'output_log'])


def _set_succeeded(job: DatabaseOperation, output: str = '') -> None:
    job.status = DatabaseOperation.STATUS_SUCCEEDED
    job.finished_at = timezone.now()
    if output:
        job.output_log = output[:16000]
    job.save(update_fields=['status', 'finished_at', 'output_log'])


def _dump_database(output_path: Path) -> tuple[str, str]:
    pg_env, dbname = _split_db_config()
    command = [
        shutil.which('pg_dump') or 'pg_dump',
        '--format=custom',
        '--no-owner',
        '--no-privileges',
        '--file',
        str(output_path),
        dbname,
    ]
    return _run_process(command, pg_env)


def _validate_restore_file(path: Path) -> None:
    max_upload_mb = int(getattr(settings, 'DATABASE_BACKUP_MAX_UPLOAD_MB', 300))
    max_upload_bytes = max_upload_mb * 1024 * 1024
    if path.stat().st_size > max_upload_bytes:
        raise RuntimeError(f'Backup file exceeds {max_upload_mb} MB upload limit.')

    pg_env, _ = _split_db_config()
    command = [shutil.which('pg_restore') or 'pg_restore', '--list', str(path)]
    _run_process(command, pg_env)


def _restore_database(input_path: Path) -> tuple[str, str]:
    pg_env, dbname = _split_db_config()
    command = [
        shutil.which('pg_restore') or 'pg_restore',
        '--clean',
        '--if-exists',
        '--no-owner',
        '--no-privileges',
        '--dbname',
        dbname,
        str(input_path),
    ]
    return _run_process(command, pg_env)


def has_running_restore_operation() -> bool:
    return DatabaseOperation.objects.filter(
        operation_type=DatabaseOperation.TYPE_RESTORE,
        status__in=[DatabaseOperation.STATUS_QUEUED, DatabaseOperation.STATUS_RUNNING],
    ).exists()


def has_running_database_operation() -> bool:
    return DatabaseOperation.objects.filter(
        status__in=[DatabaseOperation.STATUS_QUEUED, DatabaseOperation.STATUS_RUNNING],
    ).exists()


def enqueue_backup_job(*, created_by, notes: str = '', is_pre_restore_backup: bool = False) -> DatabaseOperation:
    job = DatabaseOperation.objects.create(
        operation_type=DatabaseOperation.TYPE_BACKUP,
        created_by=created_by,
        notes=notes,
        is_pre_restore_backup=is_pre_restore_backup,
    )
    thread = threading.Thread(target=run_backup_job, args=(job.pk,), daemon=True)
    thread.start()
    return job


def enqueue_restore_job(*, created_by, uploaded_file, notes: str = '') -> DatabaseOperation:
    backup_dir = _backup_dir()
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    filename = f'restore-upload-{timestamp}.dump'
    target_path = backup_dir / filename

    with target_path.open('wb') as fh:
        for chunk in uploaded_file.chunks():
            fh.write(chunk)

    file_size = target_path.stat().st_size
    file_sha = _sha256_for_file(target_path)

    job = DatabaseOperation.objects.create(
        operation_type=DatabaseOperation.TYPE_RESTORE,
        created_by=created_by,
        backup_filename=filename,
        original_upload_name=uploaded_file.name,
        file_size_bytes=file_size,
        file_sha256=file_sha,
        notes=notes,
    )

    thread = threading.Thread(target=run_restore_job, args=(job.pk,), daemon=True)
    thread.start()
    return job


def run_backup_job(job_id: int) -> None:
    job = DatabaseOperation.objects.get(pk=job_id)
    _set_running(job)

    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    output_name = f'postgres-backup-{timestamp}-job{job.pk}.dump'
    output_path = _backup_dir() / output_name

    try:
        connections.close_all()
        stdout, stderr = _dump_database(output_path)

        job.backup_filename = output_name
        job.file_size_bytes = output_path.stat().st_size
        job.file_sha256 = _sha256_for_file(output_path)
        job.save(update_fields=['backup_filename', 'file_size_bytes', 'file_sha256'])

        _set_succeeded(job, output=f'{stdout}\n{stderr}'.strip())
        logger.info('Database backup job %s finished successfully.', job.pk)
    except Exception as exc:
        _set_failed(job, str(exc))
        logger.exception('Database backup job %s failed.', job.pk)


def run_restore_job(job_id: int) -> None:
    job = DatabaseOperation.objects.get(pk=job_id)
    _set_running(job)

    backup_path = _backup_dir() / job.backup_filename
    if not backup_path.exists():
        _set_failed(job, 'Uploaded restore file no longer exists.')
        return

    pre_restore_job = None
    try:
        # Create a safety backup first so the restore remains reversible.
        pre_restore_job = enqueue_backup_job(
            created_by=job.created_by,
            notes=f'Automatic backup before restore job #{job.pk}',
            is_pre_restore_backup=True,
        )

        # Poll until the safety backup has finished.
        while True:
            pre_restore_job.refresh_from_db(fields=['status'])
            if pre_restore_job.status in (DatabaseOperation.STATUS_FAILED, DatabaseOperation.STATUS_SUCCEEDED):
                break
            threading.Event().wait(0.5)

        if pre_restore_job.status != DatabaseOperation.STATUS_SUCCEEDED:
            raise RuntimeError('Automatic pre-restore backup failed; restore aborted.')

        _validate_restore_file(backup_path)
        connections.close_all()
        stdout, stderr = _restore_database(backup_path)
        _set_succeeded(job, output=f'{stdout}\n{stderr}'.strip())
        logger.info('Database restore job %s finished successfully.', job.pk)
    except Exception as exc:
        _set_failed(job, str(exc))
        logger.exception('Database restore job %s failed.', job.pk)

