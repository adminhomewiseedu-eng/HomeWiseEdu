"""Narrow, read-only compatibility contract for the pre-assignment backend.

0014 is additive. This backend deliberately does not map or write its new data.
Do not broaden the revision allowlist without migration and preservation tests.
"""
import re

from sqlalchemy import Integer, inspect, text

from ..database import Base

SUPPORTED_REVISIONS = frozenset({
    "0013_programme_entitlements", "0014_lesson_assignments",
})


def _expression(value):
    return re.sub(r'[\s()"]', '', str(value)).lower()


def schema_is_compatible(connection):
    revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    if len(revisions) != 1 or revisions[0] not in SUPPORTED_REVISIONS:
        return False
    inspector = inspect(connection)
    # Confirm every mapped table/column still exists, not just the Alembic label.
    columns = inspector.get_multi_columns()
    for table in Base.metadata.tables.values():
        actual = {column['name'] for column in columns.get((None, table.name), [])}
        if not set(table.columns.keys()).issubset(actual):
            return False
    if revisions[0] == "0013_programme_entitlements":
        return True

    lesson_columns = {c['name']: c for c in columns.get((None, 'lessons'), [])}
    week = lesson_columns.get('curriculum_week')
    if not week or not isinstance(week['type'], Integer) or not week['nullable']:
        return False
    checks = {c['name']: _expression(c['sqltext']) for c in inspector.get_check_constraints('lessons')}
    if checks.get('ck_lesson_curriculum_week') != 'curriculum_weekisnullorcurriculum_week>0':
        return False
    assignment_columns = {c['name']: c for c in columns.get((None, 'lesson_assignments'), [])}
    required = {'id', 'child_id', 'lesson_id', 'day_number', 'assigned_by',
                'scheduled_date', 'priority', 'cancelled', 'created_at'}
    if not required.issubset(assignment_columns) or any(assignment_columns[c]['nullable'] for c in required):
        return False
    if inspector.get_pk_constraint('lesson_assignments')['constrained_columns'] != ['id']:
        return False
    fks = {tuple(fk['constrained_columns']): (fk['referred_table'], tuple(fk['referred_columns']),
            fk.get('options', {}).get('ondelete', '').upper())
           for fk in inspector.get_foreign_keys('lesson_assignments')}
    if any(fks.get((column,)) != target for column, target in {
        'child_id': ('children', ('id',), 'CASCADE'),
        'lesson_id': ('lessons', ('id',), 'RESTRICT'),
        'assigned_by': ('users', ('id',), 'RESTRICT'),
    }.items()):
        return False
    checks = {c['name']: _expression(c['sqltext']) for c in inspector.get_check_constraints('lesson_assignments')}
    if checks.get('ck_assignment_position') != 'day_number>0andpriority>=0':
        return False
    indexes = {i['name']: i for i in inspector.get_indexes('lesson_assignments')}
    for name, expected in {'ix_lesson_assignments_child_id': ['child_id'],
                           'ix_lesson_assignments_lesson_id': ['lesson_id']}.items():
        if indexes.get(name, {}).get('column_names') != expected:
            return False
    unique = indexes.get('uq_child_assignment_date', {})
    where = unique.get('dialect_options', {}).get(connection.dialect.name + '_where', '')
    return bool(unique.get('unique') and unique.get('column_names') == [
        'child_id', 'lesson_id', 'day_number', 'scheduled_date'
    ] and _expression(where) in {'cancelled=false', 'cancelled=0'})


def recovery_lesson_dependencies(db, lesson_id):
    """Protect new data even though the old ORM intentionally does not map it."""
    connection = db.connection()
    inspector = inspect(connection)
    counts = {}
    if inspector.has_table('lesson_assignments'):
        counts['lesson_assignments'] = connection.execute(text(
            'SELECT COUNT(*) FROM lesson_assignments WHERE lesson_id=:lesson_id'
        ), {'lesson_id': lesson_id}).scalar_one()
    if any(c['name'] == 'curriculum_week' for c in inspector.get_columns('lessons')):
        counts['authored_curriculum_week'] = int(connection.execute(text(
            'SELECT curriculum_week FROM lessons WHERE id=:lesson_id'
        ), {'lesson_id': lesson_id}).scalar_one_or_none() is not None)
    return counts
