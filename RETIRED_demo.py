from RETIRED_database import (
    create_database,
    add_user,
    add_project,
    create_version,
    add_file_to_version,
    approve_version,
    log_action,
    get_connection,
)

# ── Setup ─────────────────────────────────────────────────────────────────────

create_database()

# ── Create users ──────────────────────────────────────────────────────────────

add_user("alice", "alice@example.com", "hash_alice", "Author")
add_user("bob",   "bob@example.com",   "hash_bob",   "Reviewer")
#add_user("kiko(az)", "kiko@example.com", "hash_kiki", "Author")


print("Users created: alice (Author), bob (Reviewer)")

# ── Create projects ───────────────────────────────────────────────────────────

project_1 = add_project(
    title="API Documentation",
    description="Docs for the REST API",
    owner_id=1
)

project_2 = add_project(
    title="User Manual",
    description="End-user guide",
    owner_id=1
)

print(f"Projects created: #{project_1}, #{project_2}")

# ── Create versions with files ────────────────────────────────────────────────

v1 = create_version(project_1, author_id=1, message="Initial draft")
add_file_to_version(v1, "docs/intro.md",   "# Introduction\nWelcome to the API.")
add_file_to_version(v1, "docs/endpoints.md", "# Endpoints\nGET /users\nPOST /users")
log_action(1, "CREATE_VERSION", project_id=project_1, details="v1 created")

v2 = create_version(project_1, author_id=1, message="Added authentication section")
add_file_to_version(v2, "docs/intro.md",   "# Introduction\nWelcome to the API v2.")
add_file_to_version(v2, "docs/auth.md",    "# Auth\nUse Bearer token.")
approve_version(v2)
log_action(2, "APPROVE_VERSION", project_id=project_1, details="v2 approved by bob")

print(f"Versions created: v1 (Draft), v2 (Approved)")

# ── Fetch & display ───────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("FETCH: All versions of project #1")
print("=" * 50)

with get_connection() as conn:
    versions = conn.execute("""
        SELECT
            pv.version_number,
            pv.status,
            pv.message,
            u.username AS author,
            pv.created_at
        FROM project_versions pv
        JOIN users u ON u.id = pv.author_id
        WHERE pv.project_id = ?
        ORDER BY pv.version_number
    """, (project_1,)).fetchall()

    for v in versions:
        print(f"  v{v['version_number']} | {v['status']:<10} | {v['message']} | by {v['author']}")

print("\n" + "=" * 50)
print("FETCH: Files in the approved version (v2)")
print("=" * 50)

with get_connection() as conn:
    files = conn.execute("""
        SELECT vf.path, vf.content
        FROM version_files vf
        JOIN project_versions pv ON pv.id = vf.version_id
        WHERE pv.project_id = ? AND pv.status = 'Approved'
    """, (project_1,)).fetchall()

    for f in files:
        print(f"  {f['path']}")
        print(f"    → {f['content']}")

print("\n" + "=" * 50)
print("FETCH: Audit log for project #1")
print("=" * 50)

with get_connection() as conn:
    logs = conn.execute("""
        SELECT u.username, al.action, al.details, al.timestamp
        FROM audit_log al
        JOIN users u ON u.id = al.user_id
        WHERE al.project_id = ?
        ORDER BY al.timestamp
    """, (project_1,)).fetchall()

    for entry in logs:
        print(f"  [{entry['timestamp']}] {entry['username']} → {entry['action']} ({entry['details']})")
