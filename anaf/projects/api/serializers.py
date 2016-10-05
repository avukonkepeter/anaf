from anaf.projects.models import Project, TaskStatus, Milestone, Task, TaskTimeSlot
from rest_framework import serializers
from anaf.identities.api.serializers import Contact as ContactSerializer
from anaf.core.api.serializers import ProfileSerializer


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    creator = ProfileSerializer()
    client = ContactSerializer()
    manager = ContactSerializer()

    class Meta:
        model = Project


class TaskStatusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    creator = ProfileSerializer()

    class Meta:
        model = TaskStatus


class MilestoneSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    creator = ProfileSerializer()
    project = ProjectSerializer()
    status = TaskStatusSerializer()

    class Meta:
        model = Milestone


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    creator = ProfileSerializer()
    project = ProjectSerializer()
    status = TaskStatusSerializer()

    class Meta:
        model = Task


class TaskTimeSlotSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    creator = ProfileSerializer()
    task = TaskSerializer()
    user = ProfileSerializer()
    # project = ProjectSerializer()
    # status = TaskStatusSerializer()

    class Meta:
        model = TaskTimeSlot
