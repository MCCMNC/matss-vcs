"""
Unit Tests for MAT VCS
======================
Covers:
  - DBFunctions  : data access, creation, deletion, approval, path helpers
  - GUIFunctions : guiUserLogin, auditLog formatters, checkAbsPathToCodeFile

Run with:
    python -m pytest test_matvcs.py -v

Requirements:
    pip install pytest django
    DJANGO_SETTINGS_MODULE must point to a test-capable settings file
    (or the project's real config.settings with an in-memory/test DB).
"""

import os
import sys
import django

# ---------------------------------------------------------------------------
# Django bootstrap  (must happen before any model import)
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import pytest
from django.test import TestCase
from django.db import transaction

from vcs_core.models import (
    User, Repository, RepositoryMembership,
    Project, ProjectVersion, VersionFile, AuditLog,
)

# Import the modules under test AFTER django.setup()
import DBFunctions as db
import GUIFunctions as gui


# ===========================================================================
# Shared fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def clean_db():
    """Wrap every test in a rolled-back transaction so tests are isolated."""
    with transaction.atomic():
        sp = transaction.savepoint()
        yield
        transaction.savepoint_rollback(sp)


@pytest.fixture
def user(db):
    return User.objects.create(
        username="test_user",
        email="test@example.com",
        password_hash="secret123",
        role="Author",
        loginStatus=False,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create(
        username="admin_user",
        email="admin@example.com",
        password_hash="adminpass",
        role="Admin",
        loginStatus=False,
    )


@pytest.fixture
def repo(db, user):
    r = Repository.objects.create(
        title="Test Repo",
        description="desc",
        path="/some/path",
        repoType="Studio",
    )
    RepositoryMembership.objects.create(user=user, repository=r, repo_role="Admin")
    return r


@pytest.fixture
def project(db, user, repo):
    return Project.objects.create(
        title="Test Project",
        description="proj desc",
        owner=user,
        repository=repo,
        path="project_file.rpp",
    )


@pytest.fixture
def version(db, user, project):
    return ProjectVersion.objects.create(
        project=project,
        version_number=1,
        author=user,
        path="project_file.rpp",
        message="Initial version",
        status="Draft",
    )


@pytest.fixture
def version_file(db, version):
    vf = VersionFile.objects.create(path="audio/track.wav", content="raw bytes")
    vf.versions.add(version)
    return vf


# ===========================================================================
# DBFunctions – User helpers
# ===========================================================================

class TestUserHelpers:
    def test_user_login_sets_status_true(self, user):
        db.userLogIn(user)
        user.refresh_from_db()
        assert user.loginStatus is True

    def test_user_logout_sets_status_false(self, user):
        user.loginStatus = True
        user.save()
        db.userLogOut(user)
        user.refresh_from_db()
        assert user.loginStatus is False

    def test_get_or_create_user_creates_new(self):
        u = db.getOrCreateUser("brand_new", "bn@x.com", "hash", "Guest")
        assert u.username == "brand_new"
        assert User.objects.filter(username="brand_new").exists()

    def test_get_or_create_user_returns_existing(self, user):
        u = db.getOrCreateUser(user.username, "other@x.com", "other", "Guest")
        assert u.pk == user.pk  # same object, not a duplicate


# ===========================================================================
# DBFunctions – Audit log queries
# ===========================================================================

class TestAuditLogQueries:
    def test_get_user_audit_logs_returns_only_user_entries(self, user, project, version):
        AuditLog.objects.create(user=user, action="TEST_ACTION", details="d")
        other = User.objects.create(
            username="other", email="o@o.com", password_hash="x", role="Guest"
        )
        AuditLog.objects.create(user=other, action="OTHER_ACTION", details="d")

        logs = db.getUserAuditLogs(user.id)
        assert all(log.user_id == user.id for log in logs)
        assert logs.count() == 1

    def test_get_project_audit_logs(self, user, project):
        AuditLog.objects.create(user=user, project=project, action="A", details="d")
        AuditLog.objects.create(user=user, action="B", details="no project")

        logs = db.getProjectAuditLogs(project.id)
        assert all(log.project_id == project.id for log in logs)
        assert logs.count() == 1

    def test_get_project_version_audit_logs_by_id(self, user, project, version):
        AuditLog.objects.create(
            user=user, project=project, project_version=version,
            action="VER_LOG", details="d"
        )
        logs = db.getProjectVersionAuditLogsByID(version.id)
        assert len(logs) == 1
        assert logs[0].action == "VER_LOG"

    def test_get_project_version_audit_logs_invalid_id_returns_empty(self):
        assert db.getProjectVersionAuditLogsByID("not_a_number") == []
        assert db.getProjectVersionAuditLogsByID(None) == []


# ===========================================================================
# DBFunctions – Project queries
# ===========================================================================

class TestProjectQueries:
    def test_get_project_by_id(self, project):
        fetched = db.getProjectByID(project.pk)
        assert fetched.pk == project.pk

    def test_get_user_projects(self, user, project):
        projects = db.getUserProjects(user)
        assert project in projects

    def test_get_repo_projects_by_repo(self, repo, project):
        results = db.getRepoProjectsByRepo(repo)
        assert project in results

    def test_get_project_versions_by_project_id(self, project, version):
        versions = db.getProjectVersionsByProjectID(project.id)
        assert version in versions


# ===========================================================================
# DBFunctions – Project creation
# ===========================================================================

class TestProjectCreation:
    def test_add_project_to_db_creates_project_and_log(self, user, repo):
        db.addProjectToDB("New Project", "desc", user, repo)
        assert Project.objects.filter(title="New Project").exists()
        project = Project.objects.get(title="New Project")
        assert AuditLog.objects.filter(
            project=project, action="CREATE_PROJECT"
        ).exists()

    def test_add_project_to_db_idempotent(self, user, repo):
        db.addProjectToDB("Same Project", "desc", user, repo)
        db.addProjectToDB("Same Project", "desc", user, repo)
        assert Project.objects.filter(title="Same Project").count() == 1

    def test_add_next_project_version_increments_version_number(self, user, project, version):
        new_ver = db.addNextProjectVersionToDB(project, user, "Second version", "v2.rpp")
        assert new_ver is not None
        assert new_ver.version_number == 2

    def test_add_next_project_version_on_empty_project_creates_v1(self, user, repo):
        fresh_project = Project.objects.create(
            title="Fresh", description="", owner=user,
            repository=repo, path="fresh.rpp"
        )
        ver = db.addNextProjectVersionToDB(fresh_project, user, "First", "fresh.rpp")
        assert ver.version_number == 1

    def test_add_next_project_version_logs_create_version(self, user, project, version):
        new_ver = db.addNextProjectVersionToDB(project, user, "v2 msg", "v2.rpp")
        assert AuditLog.objects.filter(
            project=project, project_version=new_ver, action="CREATE_VERSION"
        ).exists()


# ===========================================================================
# DBFunctions – Version file management
# ===========================================================================

class TestVersionFileManagement:
    def test_add_version_file_to_db(self, user, version):
        vf = db.addVersionFileToDB(user, version, "src/song.wav", "bytes")
        assert vf is not None
        assert version in vf.versions.all()

    def test_add_version_file_creates_audit_log(self, user, version):
        db.addVersionFileToDB(user, version, "src/log_test.wav", "data")
        assert AuditLog.objects.filter(
            project_version=version, action="CREATE_VERSION_FILE"
        ).exists()

    def test_get_project_version_files_by_version_id(self, version, version_file):
        files = db.getProjectVersionFilesByProjectVersionID(version.id)
        assert version_file in files

    def test_get_project_version_files_nonexistent_version(self):
        result = db.getProjectVersionFilesByProjectVersionID(999999)
        assert list(result) == []

    def test_get_version_file_by_path(self, version_file):
        found = db.getVersionFileByPath(version_file.path)
        assert found is not None
        assert found.pk == version_file.pk

    def test_get_version_file_by_path_missing(self):
        assert db.getVersionFileByPath("nonexistent/path.wav") is None

    def test_is_file_linked_to_version_true(self, version, version_file):
        assert db.isFileLinkedToVersion(version_file, version) is True

    def test_is_file_linked_to_version_false(self, user, project, version_file):
        other_ver = ProjectVersion.objects.create(
            project=project, version_number=99, author=user,
            path="other.rpp", message="other", status="Draft"
        )
        assert db.isFileLinkedToVersion(version_file, other_ver) is False

    def test_link_existing_file_to_version(self, user, project, version_file):
        other_ver = ProjectVersion.objects.create(
            project=project, version_number=99, author=user,
            path="other.rpp", message="other", status="Draft"
        )
        result = db.linkExistingFileToVersion(version_file, other_ver)
        assert result is True
        assert db.isFileLinkedToVersion(version_file, other_ver)

    def test_remove_version_file_unlinks_from_version(self, user, version, version_file):
        db.removeVersionFileFromDB(user, version_file, version)
        assert not db.isFileLinkedToVersion(version_file, version)

    def test_remove_version_file_deletes_orphan(self, user, version, version_file):
        """File used by only one version should be deleted from DB after unlink."""
        file_id = version_file.pk
        db.removeVersionFileFromDB(user, version_file, version)
        assert not VersionFile.objects.filter(pk=file_id).exists()

    def test_remove_version_file_keeps_shared_file(self, user, project, version, version_file):
        """File shared by two versions must NOT be deleted when unlinked from one."""
        ver2 = ProjectVersion.objects.create(
            project=project, version_number=99, author=user,
            path="v2.rpp", message="v2", status="Draft"
        )
        version_file.versions.add(ver2)

        file_id = version_file.pk
        db.removeVersionFileFromDB(user, version_file, version)
        assert VersionFile.objects.filter(pk=file_id).exists()

    def test_get_versions_by_file_id(self, version, version_file):
        results = db.getVersionsByFileID(version_file.id)
        ids = [r['id'] for r in results]
        assert version.id in ids


# ===========================================================================
# DBFunctions – Version approval
# ===========================================================================

class TestVersionApproval:
    def test_approve_draft_version(self, user, project, version):
        result = db.approveProjectVersion(version, user, project.pk)
        assert result == 1
        version.refresh_from_db()
        assert version.status == "Approved"

    def test_approve_already_approved_returns_zero(self, user, project, version):
        version.status = "Approved"
        version.save()
        result = db.approveProjectVersion(version, user, project.pk)
        assert result == 0

    def test_approve_creates_audit_log(self, user, project, version):
        db.approveProjectVersion(version, user, project.pk)
        assert AuditLog.objects.filter(
            user=user, project_id=project.pk, action="APPROVE_VERSION"
        ).exists()


# ===========================================================================
# DBFunctions – Deletion
# ===========================================================================

class TestDeletion:
    def test_remove_project_version_from_db(self, user, project, version):
        ver_id = version.pk
        db.removeProjectVersionFromDB(user, version)
        assert not ProjectVersion.objects.filter(pk=ver_id).exists()

    def test_remove_project_from_db(self, user, repo, project, version):
        proj_id = project.pk
        db.removeProjectFromDB(user, project)
        assert not Project.objects.filter(pk=proj_id).exists()

    def test_remove_project_also_deletes_versions(self, user, repo, project, version):
        ver_id = version.pk
        db.removeProjectFromDB(user, project)
        assert not ProjectVersion.objects.filter(pk=ver_id).exists()

    def test_remove_project_logs_removal(self, user, repo, project, version):
        db.removeProjectFromDB(user, project)
        assert AuditLog.objects.filter(
            user=user, action="REMOVE_PROJECT"
        ).exists()


# ===========================================================================
# DBFunctions – Repository helpers
# ===========================================================================

class TestRepositoryHelpers:
    def test_get_user_repos_returns_correct_type(self, user, repo):
        repos = db.getUserRepos(user, repoType="Studio")
        assert repo in repos

    def test_get_user_repos_filters_by_type(self, user, repo):
        repos = db.getUserRepos(user, repoType="Code")
        assert repo not in repos

    def test_get_repo_audit_logs_by_repo(self, user, repo):
        AuditLog.objects.create(
            user=user, repository=repo, action="REPO_ACT", details="d"
        )
        logs = db.getRepoAuditLogsByRepo(repo)
        assert logs.count() >= 1
        assert all(log.repository_id == repo.id for log in logs)

    def test_create_repository_in_db(self, user):
        result = db.createRepositoryInDB(user, "Brand New Repo", "/tmp/new", "Studio")
        assert result is True
        assert Repository.objects.filter(title="Brand New Repo").exists()

    def test_create_repository_creates_admin_membership(self, user):
        db.createRepositoryInDB(user, "Membership Repo", "/tmp/mr", "Studio")
        new_repo = Repository.objects.get(title="Membership Repo")
        assert RepositoryMembership.objects.filter(
            user=user, repository=new_repo, repo_role="Admin"
        ).exists()

    def test_remove_repository_from_db(self, user, repo, project, version):
        repo_id = repo.pk
        db.removeRepositoryFromDB(user, repo, "Studio")
        assert not Repository.objects.filter(pk=repo_id).exists()


# ===========================================================================
# DBFunctions – Path helpers
# ===========================================================================

class TestPathHelpers:
    def test_get_element_relative_path_repository(self, repo):
        path = db.getElementRelativePath(repo, "Repository")
        assert path == repo.path

    def test_get_element_relative_path_project(self, project, repo):
        path = db.getElementRelativePath(project, "Project")
        assert repo.path in path
        assert project.path in path

    def test_get_element_relative_path_project_version(self, version, repo):
        path = db.getElementRelativePath(version, "ProjectVersion")
        assert repo.path in path

    def test_get_element_relative_path_version_file_with_context(self, version, version_file, repo):
        path = db.getElementRelativePath(version_file, "ProjectVersionFile", inputContext=version)
        assert repo.path in path
        assert version_file.path in path

    def test_get_element_relative_path_orphan_file(self, version_file):
        """File with no linked versions returns ORPHANED path."""
        version_file.versions.clear()
        path = db.getElementRelativePath(version_file, "ProjectVersionFile")
        assert path.startswith("ORPHANED/")

    def test_get_latest_project_version(self, user, project, version):
        v2 = ProjectVersion.objects.create(
            project=project, version_number=2, author=user,
            path="v2.rpp", message="v2", status="Draft"
        )
        latest = db.getLatestProjectVersion(project)
        assert latest.pk == v2.pk

    def test_get_latest_project_version_none_project(self):
        assert db.getLatestProjectVersion(None) is None

    def test_check_abs_path_to_code_file_match(self, project):
        project.path = "src/main.py"
        project.save()
        assert db.checkAbsPathToCodeFile(project, "/home/user/dev/main.py") is True

    def test_check_abs_path_to_code_file_mismatch(self, project):
        project.path = "src/main.py"
        project.save()
        assert db.checkAbsPathToCodeFile(project, "/home/user/dev/other.py") is False

    def test_check_abs_path_extension_matters(self, project):
        project.path = "src/main.py"
        project.save()
        assert db.checkAbsPathToCodeFile(project, "/home/user/main.txt") is False


# ===========================================================================
# GUIFunctions – Login
# ===========================================================================

class TestGuiUserLogin:
    def test_valid_login_returns_user(self, user):
        result = gui.guiUserLogin(user.username, "secret123")
        assert result is not None
        assert result.pk == user.pk

    def test_valid_login_sets_login_status(self, user):
        gui.guiUserLogin(user.username, "secret123")
        user.refresh_from_db()
        assert user.loginStatus is True

    def test_wrong_password_returns_none(self, user):
        result = gui.guiUserLogin(user.username, "wrong_password")
        assert result is None

    def test_nonexistent_user_returns_none(self):
        result = gui.guiUserLogin("ghost_user", "any_pass")
        assert result is None

    def test_empty_username_returns_none(self):
        result = gui.guiUserLogin("", "secret123")
        assert result is None


# ===========================================================================
# GUIFunctions – Audit log text formatters
# ===========================================================================

class TestAuditLogFormatters:
    def _make_log(self, user, project=None, action="TEST", details="details"):
        return AuditLog.objects.create(
            user=user, project=project, action=action, details=details
        )

    def test_audit_log_to_text_with_project(self, user, project):
        log = self._make_log(user, project=project, action="CREATE_PROJECT")
        text = gui.auditLogToText(log)
        assert "CREATE_PROJECT" in text
        assert project.title in text

    def test_audit_log_to_text_without_project(self, user):
        log = self._make_log(user, project=None, action="REPO_CREATED", details="some details")
        text = gui.auditLogToText(log)
        assert "REPO_CREATED" in text
        assert "some details" in text

    def test_audit_log_to_text_extended_includes_username(self, user, project):
        log = self._make_log(user, project=project, action="UPDATE")
        text = gui.auditLogToTextExtended(log)
        assert user.username in text

    def test_audit_log_to_text_expanded_includes_details(self, user, project):
        log = self._make_log(user, project=project, action="EXPAND_TEST", details="expanded details")
        text = gui.auditLogToTextExpanded(log)
        assert "expanded details" in text
        assert user.username in text

    def test_audit_log_timestamp_format(self, user, project):
        log = self._make_log(user, project=project)
        text = gui.auditLogToText(log)
        # Timestamp should match YYYY-MM-DD HH:MM:SS
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)


# ===========================================================================
# LoginController – handle_login validation logic
# (Tested without Qt by extracting the pure validation rule)
# ===========================================================================

class TestLoginControllerLogic:
    """
    The LoginController.handle_login method checks for empty fields before
    calling UserLogin. We replicate that guard logic here without Qt.
    """

    def _simulate_handle_login(self, username, password):
        """Mirrors the guard clause in LoginController.handle_login."""
        if not username or not password:
            return None  # short-circuit: missing field
        return gui.guiUserLogin(username, password)

    def test_missing_username_short_circuits(self):
        assert self._simulate_handle_login("", "pass") is None

    def test_missing_password_short_circuits(self):
        assert self._simulate_handle_login("user", "") is None

    def test_both_empty_short_circuits(self):
        assert self._simulate_handle_login("", "") is None

    def test_valid_credentials_reach_login(self, user):
        result = self._simulate_handle_login(user.username, "secret123")
        assert result is not None and result.pk == user.pk


# ===========================================================================
# ProjectListController – load_projects / load_audit_log logic
# (Tested without Qt by extracting the pure DB queries)
# ===========================================================================

class TestProjectListControllerLogic:
    """
    ProjectListController.load_projects filters by owner and
    load_audit_log filters AuditLog by project ordered by -timestamp.
    We test the underlying queries directly.
    """

    def test_load_projects_returns_owner_projects(self, user, project):
        other_user = User.objects.create(
            username="outsider", email="o@o.com",
            password_hash="x", role="Guest"
        )
        other_repo = Repository.objects.create(
            title="Other Repo", description="", path="/other", repoType="Studio"
        )
        other_project = Project.objects.create(
            title="Not Mine", description="", owner=other_user,
            repository=other_repo, path="other.rpp"
        )

        owned = Project.objects.filter(owner=user)
        assert project in owned
        assert other_project not in owned

    def test_load_audit_log_ordered_by_timestamp(self, user, project):
        AuditLog.objects.create(user=user, project=project, action="FIRST", details="")
        AuditLog.objects.create(user=user, project=project, action="SECOND", details="")

        logs = AuditLog.objects.filter(project=project).order_by("-timestamp")
        assert logs[0].action == "SECOND"
        assert logs[1].action == "FIRST"

    def test_load_audit_log_empty_for_new_project(self, user, repo):
        new_proj = Project.objects.create(
            title="Empty Project", description="", owner=user,
            repository=repo, path="empty.rpp"
        )
        logs = AuditLog.objects.filter(project=new_proj).order_by("-timestamp")
        assert logs.count() == 0