# -*- coding: utf-8 -*-

import handlers
from django.conf.urls import url, patterns
from anaf.core.api.auth import auth_engine
from anaf.core.api.doc import documentation_view
from anaf.core.api.resource import CsrfExemptResource

ad = {'authentication': auth_engine}

# projects resources
taskResource = CsrfExemptResource(handler=handlers.TaskHandler, **ad)
projectResource = CsrfExemptResource(handler=handlers.ProjectHandler, **ad)
statusResource = CsrfExemptResource(handler=handlers.TaskStatusHandler, **ad)
taskTimeResource = CsrfExemptResource(handler=handlers.TaskTimeHandler, **ad)
milestoneResource = CsrfExemptResource(handler=handlers.MilestoneHandler, **ad)
startTimeResource = CsrfExemptResource(
    handler=handlers.StartTaskTimeHandler, **ad)
stopTimeResource = CsrfExemptResource(
    handler=handlers.StopTaskTimeHandler, **ad)

urlpatterns = patterns('',
                       # Projects
                       url(r'^doc$', documentation_view, kwargs={'module': handlers}, name="api_projects_doc"),
                       url(r'^projects$', projectResource, name="api_projects"),
                       url(r'^project/(?P<object_ptr>\d+)', projectResource, name="api_projects"),
                       url(r'^status$', statusResource, name="api_projects_status"),
                       url(r'^status/(?P<object_ptr>\d+)', statusResource, name="api_projects_status"),
                       url(r'^milestones$', milestoneResource, name="api_projects_milestones"),
                       url(r'^milestone/(?P<object_ptr>\d+)', milestoneResource, name="api_projects_milestones"),
                       url(r'^tasks$', taskResource, name="api_projects_tasks"),
                       url(r'^task/(?P<object_ptr>\d+)', taskResource, name="api_projects_tasks"),
                       url(r'^task/times$', taskTimeResource, name="api_projects_tasktimes"),
                       url(r'^task/time/(?P<object_ptr>\d+)', taskTimeResource, name="api_projects_tasktimes"),
                       url(r'^task/time_start/(?P<task_id>\d+)', startTimeResource, name='api_projects_tasktime_start'),
                       url(r'^task/time_stop/(?P<slot_id>\d+)', stopTimeResource, name='api_projects_tasktime_stop'),
                       )
