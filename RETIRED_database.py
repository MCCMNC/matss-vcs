import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sqlite3")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["username"]
    return conn


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      VARCHAR(150) NOT NULL UNIQUE,
            email         VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role          VARCHAR(20)  NOT NULL CHECK(role IN ('Author', 'Reviewer', 'Reader', 'Admin')),
            created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       VARCHAR(255) NOT NULL,
            description TEXT,
            owner_id    INTEGER      NOT NULL,
            created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_versions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id     INTEGER     NOT NULL,
            version_number INTEGER     NOT NULL,
            status         VARCHAR(20) NOT NULL DEFAULT 'Draft'
                                       CHECK(status IN ('Draft', 'Approved', 'Rejected')),
            author_id      INTEGER     NOT NULL,
            message        TEXT,
            created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id)  REFERENCES users(id),
            UNIQUE (project_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS version_files (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER      NOT NULL,
            path       VARCHAR(500) NOT NULL,
            content    TEXT,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES project_versions(id) ON DELETE CASCADE,
            UNIQUE (version_id, path)
        );

        CREATE TABLE IF NOT EXISTS version_comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            body       TEXT    NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES project_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)    REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER      NOT NULL,
            project_id INTEGER,
            action     VARCHAR(100) NOT NULL,
            details    TEXT,
            timestamp  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_owner   ON projects(owner_id);
        CREATE INDEX IF NOT EXISTS idx_versions_project ON project_versions(project_id);
        CREATE INDEX IF NOT EXISTS idx_versions_status  ON project_versions(status);
        CREATE INDEX IF NOT EXISTS idx_vfiles_version   ON version_files(version_id);
        CREATE INDEX IF NOT EXISTS idx_comments_version ON version_comments(version_id);
        CREATE INDEX IF NOT EXISTS idx_audit_user       ON audit_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_project    ON audit_log(project_id);
    """)

    conn.commit()
    conn.close()
    print(f"Database ready: {DB_PATH}")


# ── Example helper functions you can import anywhere ──────────────────────────

def add_user(username, email, password_hash, role):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role)
        )


def get_user_by_username(username):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def add_project(title, description, owner_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (title, description, owner_id) VALUES (?, ?, ?)",
            (title, description, owner_id)
        )
        return cursor.lastrowid


def create_version(project_id, author_id, message):
    with get_connection() as conn:
        # Auto-increment version number per project
        row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM project_versions WHERE project_id = ?",
            (project_id,)
        ).fetchone()
        next_version = row[0]

        cursor = conn.execute(
            "INSERT INTO project_versions (project_id, version_number, author_id, message) VALUES (?, ?, ?, ?)",
            (project_id, next_version, author_id, message)
        )
        return cursor.lastrowid


def approve_version(version_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE project_versions SET status = 'Approved' WHERE id = ?",
            (version_id,)
        )


def reject_version(version_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE project_versions SET status = 'Rejected' WHERE id = ?",
            (version_id,)
        )


def add_file_to_version(version_id, path, content):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO version_files (version_id, path, content) VALUES (?, ?, ?)",
            (version_id, path, content)
        )


def log_action(user_id, action, project_id=None, details=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id, project_id, action, details) VALUES (?, ?, ?, ?)",
            (user_id, project_id, action, details)
        )


# ── Run once to set up the DB ─────────────────────────────────────────────────

if __name__ == "__main__":
    create_database()

    # Quick smoke test
    add_user("alice", "alice@example.com", "hashed_pw_123", "Author")
    add_user("bob",   "bob@example.com",   "hashed_pw_456", "Reviewer")

    alice = get_user_by_username("alice")
    print(f"User: {alice['username']} | Role: {alice['role']}")

    project_id = add_project("My First Doc", "A test project", owner_id=alice["id"])
    version_id = create_version(project_id, author_id=alice["id"], message="Initial draft")
    add_file_to_version(version_id, "docs/readme.md", "# Hello World")
    log_action(alice["id"], "CREATE_VERSION", project_id=project_id, details="v1 created")

    approve_version(version_id)
    log_action(alice["id"], "APPROVE_VERSION", project_id=project_id, details="v1 approved")

    print("Smoke test passed!")
