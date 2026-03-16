# demo_orm_full.py
from ConsoleUI import *
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

# ── Create users ──────────────────────────────────────────────────────────

alice, _ = User.objects.get_or_create(
    username="alice",
    defaults={
        "email": "alice@example.com",
        "password_hash": "hashed_pw_123",
        "role": "Author",
    }
)

bob, _ = User.objects.get_or_create(
    username="bob",
    defaults={
        "email": "bob@example.com",
        "password_hash": "hashed_pw_456",
        "role": "Reviewer",
    }
)

uiParagraph("Users ready: alice (Author), bob (Reviewer)")

# ── Create project ─────────────────────────────────────────────────────────

project, _ = Project.objects.get_or_create(
    title="My First Doc",
    defaults={
        "description": "A test project",
        "owner": alice
    }
)

uiParagraph(f"Project ready: #{project.pk}")

# ── Create version (auto increment) ────────────────────────────────────────

latest = (
    ProjectVersion.objects
    .filter(project=project)
    .order_by("-version_number")
    .first()
)

next_version = 1 if not latest else latest.version_number + 1

v1, created = ProjectVersion.objects.get_or_create(
    project=project,
    version_number=next_version,
    defaults={
        "author": alice,
        "message": "Initial draft"
    }
)

# ── Create file ────────────────────────────────────────────────────────────

VersionFile.objects.get_or_create(
    version=v1,
    path="docs/readme.md",
    defaults={
        "content": "# Hello World"
    }
)

# ── Log creation ───────────────────────────────────────────────────────────

AuditLog.objects.get_or_create(
    user=alice,
    project=project,
    action="CREATE_VERSION",
    details=f"v{v1.version_number} created"
)

# ── Approve version ────────────────────────────────────────────────────────

if v1.status != "Approved":
    v1.status = "Approved"
    v1.save()

AuditLog.objects.get_or_create(
    user=alice,
    project=project,
    action="APPROVE_VERSION",
    details=f"v{v1.version_number} approved"
)

uiParagraph("Smoke test passed!")

# ── Fetch & display ───────────────────────────────────────────────────────

uiParagraph("FETCHING: All versions of project")
versions = ProjectVersion.objects.filter(project=project).order_by("version_number")

for v in versions:
    print(f"  v{v.version_number} | {v.status:<10} | {v.message} | by {v.author.username}")

uiParagraph("FETCHING: Files in approved versions")

files = VersionFile.objects.filter(
    version__project=project,
    version__status="Approved"
)

uiFiles(files)
uiParagraph("FETCHING: Audit log")
logs = AuditLog.objects.filter(project=project).order_by("timestamp")
uiLogs(logs)