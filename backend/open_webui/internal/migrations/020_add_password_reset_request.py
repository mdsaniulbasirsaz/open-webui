"""Peewee migrations -- 019_add_password_reset_request.py."""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    if isinstance(database, pw.SqliteDatabase):
        _migrate_sqlite(migrator, database, fake=fake)
    else:
        _migrate_external(migrator, database, fake=fake)


def _migrate_sqlite(migrator: Migrator, database: pw.Database, *, fake=False):
    @migrator.create_model
    class PasswordResetRequest(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255, null=True)
        email = pw.CharField(max_length=255, index=True)
        token_hash = pw.CharField(max_length=255, index=True)
        expires_at = pw.BigIntegerField()
        used_at = pw.BigIntegerField(null=True)
        created_at = pw.BigIntegerField()
        last_sent_at = pw.BigIntegerField()
        revoked_at = pw.BigIntegerField(null=True)

        class Meta:
            table_name = "password_reset_request"


def _migrate_external(migrator: Migrator, database: pw.Database, *, fake=False):
    @migrator.create_model
    class PasswordResetRequest(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255, null=True)
        email = pw.CharField(max_length=255, index=True)
        token_hash = pw.CharField(max_length=255, index=True)
        expires_at = pw.BigIntegerField()
        used_at = pw.BigIntegerField(null=True)
        created_at = pw.BigIntegerField()
        last_sent_at = pw.BigIntegerField()
        revoked_at = pw.BigIntegerField(null=True)

        class Meta:
            table_name = "password_reset_request"
