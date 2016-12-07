import json
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User as DjangoUser
from anaf.core.models import User, Group, Perspective, ModuleSetting, Object
from anaf.infrastructure.models import Item, ItemValue, ItemField, ItemType, ItemStatus, ItemServicing


class InfrastructureApiTest(TestCase):
    """Infrastructure functional tests for api"""
    username = "api_test"
    password = "api_password"
    authentication_headers = {"CONTENT_TYPE": "application/json",
                              "HTTP_AUTHORIZATION": "Basic YXBpX3Rlc3Q6YXBpX3Bhc3N3b3Jk"}
    content_type = 'application/json'

    def setUp(self):
        self.group, created = Group.objects.get_or_create(name='test')
        self.user, created = DjangoUser.objects.get_or_create(username=self.username, is_staff=True)
        self.user.set_password(self.password)
        self.user.save()

        self.perspective = Perspective(name='test')
        self.perspective.set_default_user()
        self.perspective.save()
        ModuleSetting.set('default_perspective', self.perspective.id)

        self.field = ItemField(
            name='test', label='test', field_type='text')
        self.field.set_default_user()
        self.field.save()

        self.type = ItemType(name='test')
        self.type.set_default_user()
        self.type.save()
        self.type.fields.add(self.field)

        self.status = ItemStatus(name='test')
        self.status.set_default_user()
        self.status.save()

        self.item = Item(
            name='test', item_type=self.type, status=self.status)
        self.item.set_default_user()
        self.item.save()

        self.value = ItemValue(field=self.field, item=self.item)
        self.value.save()

        self.servicing = ItemServicing(name='test')
        self.servicing.set_default_user()
        self.servicing.save()

    def test_unauthenticated_access(self):
        "Test index page at /api/infrastructure/types"
        response = self.client.get('/api/infrastructure/types')
        # Redirects as unauthenticated
        self.assertEquals(response.status_code, 401)

    def test_get_fields_list(self):
        """ Test index page api/infrastructure/types """
        response = self.client.get(
            path=reverse('api_infrastructure_fields'), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_get_field(self):
        response = self.client.get(path=reverse('api_infrastructure_fields', kwargs={
            'object_ptr': self.field.id}), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_update_field(self):
        updates = {"name": "Api_name", "label": "Api label", "field_type": "text",
                   "required": True, "details": "Api details"}
        response = self.client.put(path=reverse('api_infrastructure_fields', kwargs={'object_ptr': self.field.id}),
                                   content_type=self.content_type, data=json.dumps(updates),
                                   **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEquals(data['name'], updates['name'])
        self.assertEquals(data['label'], updates['label'])
        self.assertEquals(data['field_type'], updates['field_type'])
        self.assertEquals(data['required'], updates['required'])
        self.assertEquals(data['details'], updates['details'])

    def test_get_types_list(self):
        """ Test index page api/infrastructure/types """
        response = self.client.get(
            path=reverse('api_infrastructure_types'), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_get_type(self):
        response = self.client.get(path=reverse('api_infrastructure_types', kwargs={
            'object_ptr': self.type.id}), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_update_type(self):
        updates = {"name": "Api type", "parent": None,
                   "details": "api test details", "fields": [self.field.id]}
        response = self.client.put(path=reverse('api_infrastructure_types', kwargs={'object_ptr': self.type.id}),
                                   content_type=self.content_type, data=json.dumps(updates),
                                   **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEquals(data['name'], updates['name'])
        self.assertIsNone(data['parent'])
        self.assertEquals(data['details'], updates['details'])
        for i, field in enumerate(data['fields']):
            self.assertEquals(field['id'], updates['fields'][i])

    def test_get_statuses_list(self):
        """ Test index page api/infrastructure/types """
        response = self.client.get(
            path=reverse('api_infrastructure_statuses'), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_get_status(self):
        response = self.client.get(path=reverse('api_infrastructure_statuses', kwargs={
            'object_ptr': self.status.id}), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_update_status(self):
        updates = {"name": "Api type", "active": True,
                   "hidden": False, "details": "Api details"}
        response = self.client.put(path=reverse('api_infrastructure_statuses', kwargs={'object_ptr': self.status.id}),
                                   content_type=self.content_type, data=json.dumps(updates),
                                   **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEquals(data['name'], updates['name'])
        self.assertEquals(data['active'], updates['active'])
        self.assertEquals(data['hidden'], updates['hidden'])
        self.assertEquals(data['details'], updates['details'])

    def test_get_services(self):
        """ Test index page api/infrastructure/service_records """
        response = self.client.get(
            path=reverse('api_infrastructure_service_records'), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_get_service(self):
        response = self.client.get(path=reverse('api_infrastructure_service_records', kwargs={
            'object_ptr': self.servicing.id}), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_update_service(self):
        updates = {"name": "Api servicing", "items": [self.item.id], "start_date": "2011-06-01",
                   "expiry_date": "2011-10-01", "details": "Api details"}
        response = self.client.put(
            path=reverse('api_infrastructure_service_records', kwargs={'object_ptr': self.servicing.id}),
            content_type=self.content_type, data=json.dumps(updates), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEquals(data['name'], updates['name'])
        for i, item in enumerate(data['items']):
            self.assertEquals(item['id'], updates['items'][i])
        self.assertEquals(data['start_date'], updates['start_date'])
        self.assertEquals(data['expiry_date'], updates['expiry_date'])
        self.assertEquals(data['details'], updates['details'])

    def test_get_items_list(self):
        """ Test index page api/infrastructure/items """
        response = self.client.get(
            path=reverse('api_infrastructure_items'), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_get_item(self):
        response = self.client.get(path=reverse('api_infrastructure_items', kwargs={
            'object_ptr': self.item.id}), **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

    def test_update_item(self):
        pass
        updates = {"name": "Close_API", "item_type": self.type.id,
                   "status": self.status.id, "test___1": "api test"}
        response = self.client.put(path=reverse('api_infrastructure_items', kwargs={'object_ptr': self.item.id}),
                                   content_type=self.content_type, data=json.dumps(updates),
                                   **self.authentication_headers)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEquals(data['name'], updates['name'])
        self.assertEquals(data['item_type']['id'], updates['item_type'])
        self.assertEquals(data['status']['id'], updates['status'])
        self.assertEquals(
            data['itemvalue_set'][0]["value"], updates['test___1'])
