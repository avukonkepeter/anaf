# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

from django.utils.translation import ugettext as _

from anaf.core.api.utils import rc
from piston3.handler import BaseHandler
from django.db.models import Q
from anaf.core.api.handlers import AccessHandler, ObjectHandler
from anaf.core.api.decorators import module_admin_required
from anaf.core.models import User, Group, Perspective, Module, Page, PageFolder
from anaf.core.administration.forms import PerspectiveForm, UserForm, GroupForm, PageForm, PageFolderForm

__all__ = ['GroupHandler', 'UserHandler', 'ModuleHandler',
           'PerspectiveHandler', 'PageFolderHandler', 'PageHandler']


class GroupHandler(AccessHandler):
    """Entrypoint for Group model."""
    model = Group
    form = GroupForm
    fields = ('id', 'name', 'parent', 'perspective', 'details')

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return 'api_admin_groups', [object_id]

    @staticmethod
    def perspective(data):
        return data.get_perspective()


class UserHandler(AccessHandler):
    """Entrypoint for User model."""
    model = User
    form = UserForm
    allowed_methods = ('GET', 'DELETE')
    fields = ('id', 'name', 'default_group', 'other_groups',
              'disabled', 'last_access', 'perspective')

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return ('api_admin_users', [object_id])

    @staticmethod
    def perspective(data):
        return data.get_perspective()

    def create(self, request, *args, **kwargs):
        return rc.NOT_IMPLEMENTED

    def update(self, request, *args, **kwargs):
        return rc.NOT_IMPLEMENTED

    @module_admin_required()
    def delete(self, request, *args, **kwargs):
        pkfield = self.model._meta.pk.name

        if pkfield in kwargs:
            try:
                profile = self.model.objects.get(pk=kwargs.get(pkfield))

                if profile == request.user.profile:
                    self.status = 401
                    return _("This is you!")
                else:
                    profile.delete()
                    return rc.DELETED
            except self.model.MultipleObjectsReturned:
                return rc.DUPLICATE_ENTRY
            except self.model.DoesNotExist:
                return rc.NOT_HERE
        else:
            return rc.BAD_REQUEST


class ModuleHandler(BaseHandler):
    """Entrypoint for Module model."""
    allowed_methods = ('GET',)
    model = Module
    exclude = ('object_type', 'object_ptr', 'object_name')

    read = module_admin_required()(BaseHandler.read)

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return 'api_admin_modules', [object_id]


class PerspectiveHandler(ObjectHandler):
    "Entrypoint for Perspective model."
    model = Perspective
    form = PerspectiveForm

    fields = ('id',) + form._meta.fields

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return ('api_admin_perspectives', [object_id])

    def check_create_permission(self, request, mode):
        return request.user.profile.is_admin('anaf.core')

    def check_instance_permission(self, request, inst, mode):
        return request.user.profile.is_admin('anaf.core')

    @module_admin_required()
    def delete_instance(self, request, inst):
        # Don't let users delete their last perspective
        other_perspectives = Perspective.objects.filter(
            trash=False).exclude(id=inst.id)
        admin_module = Module.objects.all().filter(name='anaf.core')[0]
        if not other_perspectives:
            self.status = 401
            return _("This is your only Perspective.")
        elif not other_perspectives.filter(Q(modules=admin_module) | Q(modules__isnull=True)):
            self.status = 401
            return _("This is your only Perspective with Administration module. You would be locked out!")
        elif 'trash' in request.REQUEST:
            inst.trash = True
            inst.save()
            return inst
        else:
            inst.delete()
            return rc.DELETED

    @module_admin_required()
    def update(self, request, *args, **kwargs):
        if request.data is None:
            return rc.BAD_REQUEST

        pkfield = kwargs.get(self.model._meta.pk.name) or request.data.get(
            self.model._meta.pk.name)

        if not pkfield:
            return rc.BAD_REQUEST

        try:
            obj = self.model.objects.get(pk=pkfield)
        except self.model.ObjectDoesNotExist:
            return rc.NOT_FOUND

        attrs = self.flatten_dict(request)

        form = self.form(instance=obj, **attrs)
        if form.is_valid():
            perspective = form.save()

            admin_module = Module.objects.filter(name='anaf.core')[0]
            other_perspectives = Perspective.objects.filter(
                trash=False).exclude(id=perspective.id)
            modules = perspective.modules.all()
            if modules and admin_module not in modules and \
                    not other_perspectives.filter(Q(modules=admin_module) | Q(modules__isnull=True)):
                perspective.modules.add(admin_module)
                request.session['message'] = _(
                        "This is your only Perspective with Administration module. You would be locked out!")
            return obj
        else:
            self.status = 400
            return form.errors


class PageFolderHandler(ObjectHandler):
    """Entrypoint for PageFolder model."""
    model = PageFolder
    form = PageFolderForm

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return 'api_admin_folders', [object_id]

    def check_instance_permission(self, request, inst, mode):
        return request.user.profile.is_admin('anaf.core')

    def flatten_dict(self, request):
        return {'data': super(PageFolderHandler, self).flatten_dict(request.data)}


class PageHandler(ObjectHandler):
    """Entrypoint for Page model."""
    model = Page
    form = PageForm

    @classmethod
    def resource_uri(cls, obj=None):
        object_id = "id"
        if obj is not None:
            object_id = obj.id
        return 'api_admin_pages', [object_id]

    def check_instance_permission(self, request, inst, mode):
        return request.user.profile.is_admin('anaf.core')

    def flatten_dict(self, request):
        return {'data': super(PageHandler, self).flatten_dict(request.data)}
