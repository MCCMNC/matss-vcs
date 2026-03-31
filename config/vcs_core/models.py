from django.db import models

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
    # KEEPING THIS FOR COMPATIBILITY: Acts as a 'Global' or 'Default' role
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    loginStatus = models.BooleanField(default=False)

    # NEW: Many-to-Many relationship with Repository
    repositories = models.ManyToManyField(
        'Repository',
        through='RepositoryMembership',
        related_name='members'
    )

    def __str__(self):
        return self.username


class Repository(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    path = models.CharField(max_length=255, default="unknown")

    def __str__(self):
        return self.title


# NEW: The 'Bridge' table that handles repo-specific roles
class RepositoryMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)

    # This role is specific ONLY to this repository
    repo_role = models.CharField(
        max_length=20,
        choices=User.ROLE_CHOICES,
        default="Reader"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "repository")


class Project(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    path = models.CharField(max_length=255, default="unknown")

    class Meta:
        unique_together = ("project", "version_number")


class VersionFile(models.Model):
    versions = models.ManyToManyField(ProjectVersion, related_name="version_files")
    path = models.CharField(max_length=255, default="unknown")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Version File"


class VersionComment(models.Model):
    version = models.ForeignKey(ProjectVersion, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    project_version = models.ForeignKey('ProjectVersion', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    repository = models.ForeignKey('Repository', on_delete=models.SET_NULL,null=True,blank=True)