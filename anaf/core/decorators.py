"""
Core decorators for views
"""

import re
import json
from threading import local
from functools import wraps
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse, NoReverseMatch
from django.http.response import HttpResponseNotFound
from django.utils.decorators import available_attrs
from django.utils.html import escape
from jinja2.loaders import TemplateNotFound
from conf import settings
from models import Module
from rss import verify_secret_key


def apifirst(viewfunc):
    """
    Used to mark a method on a ViewSet to prioritize api formats.
    So if format is not one of the accepted formats use the parent method to process request
    """
    def decorator(self, request, *args, **kwargs):
        if request.accepted_renderer.format in self.accepted_formats:
            return viewfunc(self, request, *args, **kwargs)
        parent_viewfunc = getattr(super(self.__class__, self), viewfunc.__name__)
        return parent_viewfunc(request, *args, **kwargs)
    return decorator


def load_modules_regexp():
    modules_regexp = getattr(local, 'modules_regexp', None)
    if not modules_regexp:
        modules_regexp = {}  # should be a dict with module name for key and regexp list
        for name in Module.objects.all().values_list('name', flat=True):
            try:
                import_name = name + "." + settings.ANAF_MODULE_IDENTIFIER
                hmodule = __import__(import_name, fromlist=[str(name)])
                modules_regexp[name] = hmodule.URL_PATTERNS
            except ImportError:
                pass
            except AttributeError:
                pass
    return modules_regexp


def get_active_module(path):
    for name, urls in load_modules_regexp().items():
        for regexp in urls:
            if re.match(regexp, path):
                return Module.objects.get(name=name)


def mylogin_required(f):
    """ Check that the user has write access to the anaf.core module """

    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated():
            user = request.user.profile
            active = get_active_module(request.path)
            if active:
                if user.get_perspective().get_modules().filter(name=active.name).exists() and \
                        user.has_permission(active):
                    return f(request, *args, **kwargs)
                else:
                    if request.path[:3] == '/m/':
                        return HttpResponseRedirect('/m/user/denied')
                    return HttpResponseRedirect('/user/denied')
            else:
                return f(request, *args, **kwargs)
        else:
            if request.path[:3] == '/m/':
                return HttpResponseRedirect('/m/accounts/login')
            if 'response_format' in kwargs and kwargs['response_format'] == 'rss' and 'secret' in request.GET and \
                    verify_secret_key(request):
                return f(request, *args, **kwargs)
            return HttpResponseRedirect('/accounts/login')

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__

    return wrap


def module_admin_required(module_name=None):
    """ Check that the user has write access to the core module """

    if not module_name:
        module_name = 'anaf.core'

    def wrap(f):
        "Wrap"

        def wrapped_f(request, *args, **kwargs):
            "Wrapped"

            if request.user.profile.is_admin(module_name):
                return f(request, *args, **kwargs)
            else:
                return HttpResponseRedirect(reverse('user_denied'))

        wrapped_f.__doc__ = f.__doc__
        wrapped_f.__name__ = f.__name__

        return wrapped_f

    return wrap


def _is_full_redirect(redirect_url):
    "Returns True if this page requires full reload with AJAX enabled"
    redirect_views = settings.ANAF_AJAX_RELOAD_ON_REDIRECT
    for view in redirect_views:
        url = ''
        try:
            url = reverse(view)
        except NoReverseMatch:
            pass
        if url and url == redirect_url:
            return True
    return False


def handle_response_format(f):
    """ Handle response format for a view """

    def wrap(request, *args, **kwargs):
        "Wrap"
        try:
            if 'response_format' in kwargs:
                response_format = kwargs['response_format']
                if not response_format:
                    response_format = 'html'
                    kwargs['response_format'] = response_format

                response = f(request, *args, **kwargs)
                if response_format == 'ajax':
                    if response.__class__ == HttpResponseRedirect:
                        location = response['Location']
                        if not _is_full_redirect(location):
                            response = HttpResponse(json.dumps({'redirect': location}),
                                                    content_type=settings.ANAF_RESPONSE_FORMATS['ajax'])
                        else:
                            if '.ajax' in location:
                                location = str(location).replace('.ajax', '')
                            response = HttpResponse(json.dumps({'redirect_out': location}),
                                                    content_type=settings.ANAF_RESPONSE_FORMATS['ajax'])
                    elif hasattr(request, 'redirect'):
                        location = request.redirect
                        response = HttpResponse(json.dumps({'redirect': location}),
                                                content_type=settings.ANAF_RESPONSE_FORMATS['ajax'])
                    elif 'Content-Disposition' in response and \
                            response['Content-Type'] not in settings.ANAF_RESPONSE_FORMATS.values():
                        location = request.get_full_path()
                        if '.ajax' in location:
                            location = str(location).replace('.ajax', '')
                        response = HttpResponse(json.dumps({'redirect_out': location}),
                                                content_type=settings.ANAF_RESPONSE_FORMATS['ajax'])

                return response
            else:
                return f(request, *args, **kwargs)
        except TemplateNotFound:
            response_format = None
            if 'response_format' in kwargs:
                response_format = kwargs['response_format']
            if not response_format:
                response_format = 'html'
                kwargs['response_format'] = response_format
            if settings.DEBUG:
                raise
            raise Http404(
                'This page is not available in ' + response_format.upper() + ' format')

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__

    return wrap


# Forms pre-processing

from django.forms.forms import BoundField


def add_required_label_tag(original_function):
    """Adds the 'required' CSS class and an asterisks to required field labels."""

    def required_label_tag(self, contents=None, attrs=None):
        "Required label tag"
        contents = contents or escape(self.label)
        if self.field.required:
            if not self.label.endswith(" *"):
                self.label += " *"
                contents += " *"
            attrs = {'class': 'required'}
        return original_function(self, contents, attrs)

    return required_label_tag


def preprocess_form():
    "Add Asterisk To Field Labels"
    BoundField.label_tag = add_required_label_tag(BoundField.label_tag)


def require_response_format(format_list):
    """
    Decorator to make a view only accept particular response formats.  Usage::

        @require_response_format(["html", "json"])
        def my_view(request, response_format):
            # I can assume now that only html or json response_format
            ...

    Note that response formats should be in lowercase.
    """

    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            response_format = kwargs.get('response_format')
            if not response_format:
                # If format is None or empty then it will be whatever the view defined as default
                del kwargs['response_format']
            elif response_format not in format_list:
                return HttpResponseNotFound('View not available in the requested format. Available in %s' % format_list)
            return func(request, *args, **kwargs)

        return inner

    return decorator
