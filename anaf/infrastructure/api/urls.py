# -*- coding: utf-8 -*-

import handlers
from django.conf.urls import url, patterns
from anaf.core.api.auth import auth_engine
from anaf.core.api.doc import documentation_view
from anaf.core.api.resource import CsrfExemptResource

ad = {'authentication': auth_engine}

# infrastructure resources
typeResource = CsrfExemptResource(handler=handlers.ItemTypeHandler, **ad)
fieldResource = CsrfExemptResource(handler=handlers.ItemFieldHandler, **ad)
itemResource = CsrfExemptResource(handler=handlers.ItemHandler, **ad)
statusResource = CsrfExemptResource(handler=handlers.ItemStatusHandler, **ad)
serviceRecordResource = CsrfExemptResource(
    handler=handlers.ItemServicingHandler, **ad)
locationResource = CsrfExemptResource(handler=handlers.LocationHandler, **ad)

urlpatterns = patterns('',
                       # Infrastructure
                       url(r'^doc$', documentation_view, kwargs={'module': handlers}, name="api_infrastructure_doc"),
                       url(r'^fields$', fieldResource, name="api_infrastructure_fields"),
                       url(r'^field/(?P<object_ptr>\d+)', fieldResource, name="api_infrastructure_fields"),
                       url(r'^types$', typeResource, name="api_infrastructure_types"),
                       url(r'^type/(?P<object_ptr>\d+)', typeResource, name="api_infrastructure_types"),
                       url(r'^statuses$', statusResource, name="api_infrastructure_statuses"),
                       url(r'^status/(?P<object_ptr>\d+)', statusResource, name="api_infrastructure_statuses"),
                       url(r'^items$', itemResource, name="api_infrastructure_items"),
                       url(r'^item/(?P<object_ptr>\d+)', itemResource, name="api_infrastructure_items"),
                       url(r'^service_records$', serviceRecordResource, name="api_infrastructure_service_records"),
                       url(r'^service_record/(?P<object_ptr>\d+)', serviceRecordResource,
                           name="api_infrastructure_service_records"),
                       url(r'^locations$', locationResource, name="api_infrastructure_locations"),
                       url(r'^location/(?P<object_ptr>\d+)', locationResource, name="api_infrastructure_locations"),
                       )
