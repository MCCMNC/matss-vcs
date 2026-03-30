from django.db import models

## UNVERIFIED FILE
class User(models.Model):

    ROLE_CHOICES = [
        ("Author", "Author"),
        ("Reviewer", "Reviewer"),
        ("Reader", "Reader"),
        ("Admin", "Admin"),
    ]

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    loginStatus = models.BooleanField(default=False)

class Repository(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    path = models.CharField(max_length=255, default="unknown")

class Project(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        null=True,  # Critical: Allows existing projects to have no repo
        blank=True  # Critical: Allows forms to be saved without a repo
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    path = models.CharField(max_length=255, default="unknown")
    created_at = models.DateTimeField(auto_now_add=True)


class ProjectVersion(models.Model):

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    version_number = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft"
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    path = models.CharField(max_length=255, default="unknown")

    class Meta:
        unique_together = ("project", "version_number")


class VersionFile(models.Model):
    # Change ForeignKey to ManyToManyField
    versions = models.ManyToManyField(
        ProjectVersion,
        related_name="version_files"
    )

    path = models.CharField(max_length=255, default="unknown")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Note: 'unique_together' is no longer strictly enforceable at the DB level
        # for ManyToMany relationships in the same way.
        # Uniqueness is now handled via application logic or a 'through' model.
        verbose_name = "Version File"

    def __str__(self):
        return self.path


class VersionComment(models.Model):

    version = models.ForeignKey(ProjectVersion, on_delete=models.CASCADE)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    body = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True
    )
    # Add this line:
    project_version = models.ForeignKey(
        'ProjectVersion', # Use string if ProjectVersion is defined later in the file
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)