from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        depth = 1

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = '__all__'
        depth = 1

class RepositoryMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepositoryMembership
        fields = '__all__'
        depth = 1

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        depth = 1

class ProjectVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectVersion
        fields = '__all__'
        depth = 1

    
class VersionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionFile
        fields = '__all__'
        depth = 1

class VersionCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionComment
        fields = '__all__'
        depth = 1

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        depth = 1