# demo_orm_full.py
from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

# ── Setup ────────────────────────────────────────────────────────────────

# No need for create_database(); Django migrations already set up the DB

# ── Create users ──────────────────────────────────────────────────────────
alice = User.objects.create(
    username="alice",
    email="alice@example.com",
    password_hash="hashed_pw_123",
    role="Author"
)

bob = User.objects.create(
    username="bob",
    email="bob@example.com",
    password_hash="hashed_pw_456",
    role="Reviewer"
)

print("Users created: alice (Author), bob (Reviewer)")

# ── Create projects ───────────────────────────────────────────────────────
project = Project.objects.create(
    title="My First Doc",
    description="A test project",
    owner=alice
)

print(f"Project created: #{project.id}")

# ── Create versions and files ─────────────────────────────────────────────
# Initial draft
v1 = ProjectVersion.objects.create(
    project=project,
    version_number=1,
    author=alice,
    message="Initial draft"
)

VersionFile.objects.create(
    version=v1,
    path="docs/readme.md",
    content="# Hello World"
)

AuditLog.objects.create(
    user=alice,
    project=project,
    action="CREATE_VERSION",
    details="v1 created"
)

# Approve version
v1.status = "Approved"
v1.save()

AuditLog.objects.create(
    user=alice,
    project=project,
    action="APPROVE_VERSION",
    details="v1 approved"
)

print("Smoke test passed!")

# ── Fetch & display ───────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("FETCH: All versions of project")
print("=" * 50)

versions = ProjectVersion.objects.filter(project=project).order_by("version_number")
for v in versions:
    print(f"  v{v.version_number} | {v.status:<10} | {v.message} | by {v.author.username}")

print("\n" + "=" * 50)
print("FETCH: Files in approved versions")
print("=" * 50)

files = VersionFile.objects.filter(version__project=project, version__status="Approved")
for f in files:
    print(f"  {f.path}")
    print(f"    → {f.content}")

print("\n" + "=" * 50)
print("FETCH: Audit log")
print("=" * 50)

logs = AuditLog.objects.filter(project=project).order_by("timestamp")
for entry in logs:
    print(f"  [{entry.timestamp}] {entry.user.username} → {entry.action} ({entry.details})")