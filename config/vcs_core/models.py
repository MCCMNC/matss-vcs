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

class Project(models.Model):

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

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

    class Meta:
        unique_together = ("project", "version_number")


class VersionFile(models.Model):

    version = models.ForeignKey(ProjectVersion, on_delete=models.CASCADE)

    path = models.CharField(max_length=500)

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("version", "path")


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

    action = models.CharField(max_length=100)

    details = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)