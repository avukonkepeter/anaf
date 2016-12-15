"""
Projects integration with Events module

Provides Tasks and Milestones as EventRenderer instances
"""
from __future__ import unicode_literals
from models import Task, Milestone
from anaf.core.models import Object
from anaf.events.rendering import EventRenderer
from django.db.models import Q


def get_events(request):
    """Return a list of EventRenderers from available Tasks and Milestones"""
    events = []

    query = (Q(start_date__isnull=False) | Q(end_date__isnull=False)) & Q(
        status__hidden=False)
    tasks = Object.filter_by_request(
        request, manager=Task.objects.filter(query))
    for task in tasks:
        if task.end_date:
            event = EventRenderer(
                task.name, task.start_date, task.end_date, task.get_absolute_url())
        else:
            event = EventRenderer(
                task.name, None, task.start_date, task.get_absolute_url())
        event.css_class += " projects-calendar-task"
        events.append(event)

    query = (Q(start_date__isnull=False) | Q(end_date__isnull=False)) & Q(
        status__hidden=False)
    milestones = Object.filter_by_request(
        request, manager=Milestone.objects.filter(query))
    for milestone in milestones:
        name = "&nbsp;&nbsp;&nbsp;&nbsp;" + milestone.name
        if milestone.end_date:
            event = EventRenderer(name, milestone.start_date, milestone.end_date,
                                  milestone.get_absolute_url())
        else:
            event = EventRenderer(
                name, None, milestone.start_date, milestone.get_absolute_url())
        event.css_class += " projects-calendar-milestone"
        events.append(event)

    return events
