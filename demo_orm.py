# demo_orm.py
from vcs_core.models import User, Project, ProjectVersion, VersionFile, AuditLog

# ── Create users ──────────────────────────────────────────────────────────────
alice = User.objects.create(
    username="alice",
    email="alice@example.com",
    password_hash="hash_alice",
    role="Author"
)
bob = User.objects.create(
    username="bob",
    email="bob@example.com",
    password_hash="hash_bob",
    role="Reviewer"
)
# Uncomment to add more users
# kiko = User.objects.create(username="kiko(az)", email="kiko@example.com", password_hash="hash_kiki", role="Author")

print("Users created: alice (Author), bob (Reviewer)")

# ── Create projects ───────────────────────────────────────────────────────────
project_1 = Project.objects.create(
    title="API Documentation",
    description="Docs for the REST API",
    owner=alice
)

project_2 = Project.objects.create(
    title="User Manual",
    description="End-user guide",
    owner=alice
)

print(f"Projects created: #{project_1.id}, #{project_2.id}")

# ── Create versions with files ────────────────────────────────────────────────
# v1 draft
v1 = ProjectVersion.objects.create(
    project=project_1,
    version_number=1,
    author=alice,
    message="Initial draft"
)

VersionFile.objects.create(version=v1, path="docs/intro.md", content="# Introduction\nWelcome to the API.")
VersionFile.objects.create(version=v1, path="docs/endpoints.md", content="# Endpoints\nGET /users\nPOST /users")

AuditLog.objects.create(user=alice, project=project_1, action="CREATE_VERSION", details="v1 created")

# v2 approved
v2 = ProjectVersion.objects.create(
    project=project_1,
    version_number=2,
    author=alice,
    message="Added authentication section",
    status="Approved"
)

VersionFile.objects.create(version=v2, path="docs/intro.md", content="# Introduction\nWelcome to the API v2.")
VersionFile.objects.create(version=v2, path="docs/auth.md", content="# Auth\nUse Bearer token.")

AuditLog.objects.create(user=bob, project=project_1, action="APPROVE_VERSION", details="v2 approved by bob")

print(f"Versions created: v1 (Draft), v2 (Approved)")

# ── Fetch & display ───────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("FETCH: All versions of project #1")
print("=" * 50)

versions = ProjectVersion.objects.filter(project=project_1).order_by("version_number")
for v in versions:
    print(f"  v{v.version_number} | {v.status:<10} | {v.message} | by {v.author.username}")

print("\n" + "=" * 50)
print("FETCH: Files in the approved version (v2)")
print("=" * 50)

files = VersionFile.objects.filter(version__project=project_1, version__status="Approved")
for f in files:
    print(f"  {f.path}")
    print(f"    → {f.content}")

print("\n" + "=" * 50)
print("FETCH: Audit log for project #1")
print("=" * 50)

logs = AuditLog.objects.filter(project=project_1).order_by("timestamp")
for entry in logs:
    print(f"  [{entry.timestamp}] {entry.user.username} → {entry.action} ({entry.details})")