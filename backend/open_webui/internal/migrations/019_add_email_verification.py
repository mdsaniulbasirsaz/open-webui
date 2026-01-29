"""Peewee migrations -- 019_add_email_verification.py."""

from peewee_migrate import Migrator
import peewee as pw

# Placeholder to satisfy migration sequence. Email verification structures already exist.
def migrate(migrator: Migrator, database: pw.Database, *, fake: bool = False):
    return

def rollback(migrator: Migrator, database: pw.Database, *, fake: bool = False):
    return
