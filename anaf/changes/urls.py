"""
Change Control module URLs
"""
from django.conf.urls import url, patterns

from anaf.changes import views

urlpatterns = patterns('anaf.changes.views',
                       url(r'^(\.(?P<response_format>\w+))?$', views.index, name='changes_index'),
                       url(r'^owned(\.(?P<response_format>\w+))?$', views.index_owned, name='changes_index_owned'),
                       url(r'^resolved(\.(?P<response_format>\w+))?$', views.index_resolved,
                           name='changes_index_resolved'),

                       # Statuses
                       url(r'^status/view/(?P<status_id>\d+)(\.(?P<response_format>\w+))?/?$', views.status_view,
                           name='changes_status_view'),
                       url(r'^status/edit/(?P<status_id>\d+)(\.(?P<response_format>\w+))?/?$', views.status_edit,
                           name='changes_status_edit'),
                       url(r'^status/delete/(?P<status_id>\d+)(\.(?P<response_format>\w+))?/?$', views.status_delete,
                           name='changes_status_delete'),
                       url(r'^status/add(\.(?P<response_format>\w+))?/?$', views.status_add, name='changes_status_add'),

                       # Sets
                       url(r'^set/view/(?P<set_id>\d+)(\.(?P<response_format>\w+))?/?$', views.set_view,
                           name='changes_set_view'),
                       url(r'^set/edit/(?P<set_id>\d+)(\.(?P<response_format>\w+))?/?$', views.set_edit,
                           name='changes_set_edit'),
                       url(r'^set/delete/(?P<set_id>\d+)(\.(?P<response_format>\w+))?/?$', views.set_delete,
                           name='changes_set_delete'),
                       url(r'^set/add(\.(?P<response_format>\w+))?/?$', views.set_add, name='changes_set_add'),

                       # Settings
                       url(r'^settings/view(\.(?P<response_format>\w+))?/?$', views.settings_view,
                           name='changes_settings_view'),
                       url(r'^settings/edit(\.(?P<response_format>\w+))?/?$', views.settings_edit,
                           name='changes_settings_edit'),
                       )
