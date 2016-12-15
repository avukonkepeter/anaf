"""
Rendering routines
"""
from __future__ import unicode_literals
from django.core.exceptions import ImproperlyConfigured
from django.utils.six import string_types
from django.http import HttpResponse
from django.contrib.sites.models import RequestSite
from django.utils.translation import ugettext as _
from django.forms import BaseForm
from django.contrib import messages
from django.template import RequestContext
from jinja2 import Template
from coffin.template import loader
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer, BrowsableAPIRenderer

from conf import settings
from models import UpdateRecord
from ajax.converter import preprocess_context as preprocess_context_ajax, convert_to_ajax
import hashlib
import random
import os
import codecs
import re
import subprocess
import json


def _preprocess_context_html(context):
    "Prepares context to be rendered for HTML"

    # Process popuplink fields
    for key in context:
        if isinstance(context[key], BaseForm):
            form = context[key]
            for fname in form.fields:
                field = form.fields[fname]
                try:
                    # find popuplink fields
                    if field.widget.attrs and 'popuplink' in field.widget.attrs:
                        field.help_text += '<a href="{0!s}" field="id_{1!s}" id="link-{2!s}" class="inline-link add-link popup-link">{3!s}</a>'.format(field.widget.attrs['popuplink'], fname, fname, _("New"))
                except Exception:
                    pass

    return context


def render_to_string(template_name, context=None, context_instance=None, response_format='html'):
    """Picks up the appropriate template to render to string"""
    if context is None:
        context = {}
    if isinstance(template_name, string_types):
        template_name = (template_name,)

    if not response_format or 'pdf' in response_format or response_format not in settings.ANAF_RESPONSE_FORMATS:
        response_format = 'html'

    template_name = map(lambda name: name if "." + response_format in name else name + "." + response_format,
                        template_name)
    template_name += map(lambda name: response_format + "/" + name, template_name)

    context['response_format'] = response_format
    if context_instance:
        context['site_domain'] = RequestSite(context_instance['request']).domain

    context = _preprocess_context_html(context)

    rendered_string = loader.render_to_string(template_name, context, context_instance)
    return rendered_string


def render_to_ajax(template_name, context=None, context_instance=None):
    """Render request into JSON object to be handled by AJAX on the server-side"""
    if context is None:
        context = {}
    response_format = 'html'
    if 'response_format_tags' not in context:
        context['response_format_tags'] = 'ajax'

    context = preprocess_context_ajax(context)
    content = render_to_string(
        template_name, context, context_instance, response_format)
    content = convert_to_ajax(content, context_instance)
    context['content'] = json.dumps(content)

    notifications = []
    if context_instance and 'request' in context_instance:
        request = context_instance['request']
        maxmsgs = 5
        try:
            for message in list(messages.get_messages(request))[:maxmsgs]:
                msgtext = str(message)
                if 'updaterecord:' in msgtext[:13]:
                    try:
                        update_id = int(msgtext.split(':', 1)[1])
                        update = UpdateRecord.objects.get(pk=update_id)
                        message = {'message': update.get_full_message(),
                                   'tags': message.tags}
                        if update.author:
                            if update.record_type == 'manual' or update.record_type == 'share':
                                try:
                                    message[
                                        'image'] = update.author.get_contact().get_picture()
                                except:
                                    pass
                            message['title'] = str(update.author)
                        for obj in update.about.all():
                            message['message'] = "({0!s}) {1!s}:<br />{2!s}".format(
                                obj.get_human_type(), str(obj), message['message'])
                        notifications.append(message)
                    except:
                        pass
                else:
                    notifications.append({'message': str(message),
                                          'tags': message.tags})
        except:
            pass
    context['notifications'] = json.dumps(notifications)

    rendered_string = render_to_string('ajax_base', context, context_instance, response_format='json')

    return rendered_string


def render_to_response(template_name, context=None, context_instance=None, response_format='html'):
    "Extended render_to_response to support different formats"
    if context is None:
        context = {}
    if not response_format:
        response_format = 'html'

    if response_format not in settings.ANAF_RESPONSE_FORMATS:
        response_format = 'html'

    content_type = settings.ANAF_RESPONSE_FORMATS[response_format]

    if 'pdf' in response_format:
        while True:
            hasher = hashlib.md5()
            hasher.update(str(random.random()))
            filepath = u"pdfs/" + hasher.hexdigest()
            output = settings.MEDIA_ROOT + filepath
            if not os.path.exists(output + ".pdf"):
                break

        while True:
            hasher = hashlib.md5()
            hasher.update(str(random.random()))
            filepath = hasher.hexdigest() + ".html"
            source = getattr(settings, 'WKCWD', './') + filepath
            if not os.path.exists(source):
                break

        page_size = "A4"
        orientation = "portrait"

        rendered_string = render_to_string(
            template_name, context, context_instance, response_format)

        with codecs.open(source, encoding='utf-8', mode='w') as f:
            pdf_string = str(rendered_string)

            if context_instance and context_instance['request']:
                pdf_string = pdf_string.replace(
                    "a href=\"/", "a href=\"http://" + RequestSite(context_instance['request']).domain + "/")

            pdf_string.replace("href=\"/", "href=\"")

            pattern = """Content-Type: text/html|<td>\n\W*<div class="content-list-tick">\n\W.*\n.*</div></td>|<th scope="col">Select</th>"""
            pdf_string = re.sub(pattern, "", pdf_string).replace(
                '/static/', 'static/')

            f.write(pdf_string)

        wkpath = getattr(settings, 'WKPATH', './bin/wkhtmltopdf-i386')
        x = subprocess.Popen("{0!s} --print-media-type --orientation {1!s} --page-size {2!s} {3!s} {4!s}".format(wkpath,
                              orientation,
                              page_size,
                              source,
                              output),
                             shell=True,
                             cwd=getattr(settings, 'WKCWD', './'))
        x.wait()

        with open(output) as f:
            response = HttpResponse(f.read(), content_type='application/pdf')

        os.remove(output)
        os.remove(source)

        # response['Content-Disposition'] = 'attachment; filename=%s'%(pdf_name)

        return response

    if 'ajax' in response_format:
        rendered_string = render_to_ajax(
            template_name, context, context_instance)

    else:

        if response_format == 'html' and context_instance and context_instance['request'].path[:3] == '/m/':
            context['response_format'] = response_format = 'mobile'

        if settings.ANAF_FORCE_AJAX_RENDERING:
            context = preprocess_context_ajax(context)

        rendered_string = render_to_string(
            template_name, context, context_instance, response_format)

    response = HttpResponse(rendered_string, content_type=content_type)

    return response


def render_string_template(template_string, context=None, context_instance=None):
    """
    Performs rendering using template_string instead of a file, and context.
    context_instance is only used to feed user into context (unless already defined)

    Returns string.
    """
    if context is None:
        context = {}
    template = Template(template_string)
    if 'user' not in context and context_instance and 'request' in context_instance:
        context.update({'user': context_instance['request']})

    return template.render(context)


def get_template_source(template_name, response_format='html'):
    "Returns source of the template file"

    if not response_format or 'pdf' in response_format or response_format not in settings.ANAF_RESPONSE_FORMATS:
        response_format = 'html'

    if not ("." + response_format) in template_name:
        template_name += "." + response_format

    template_name = response_format + "/" + template_name

    t = loader.get_template(template_name)
    f = open(t.filename, 'r')

    return f.read()


class JinjaRenderer(TemplateHTMLRenderer):
    """Same as the html renderer, but it will use jinja instead of the standard django template"""
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders data to HTML, using Jinja template rendering.

        The template name is determined by (in order of preference):

        1. An explicit .template_name set on the response.
        2. An explicit .template_name set on this class.
        3. The return result of calling view.get_template_names().
        """
        renderer_context = renderer_context or {}
        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        if response.exception:
            if response.status_code == 401 and not request.user.is_authenticated():
                template_names = 'core/user_login.html'
            else:
                template_names = [name % {'status_code': response.status_code} for name in self.exception_template_names]
        else:
            try:
                template_names = self.get_template_names(response, view)
            except ImproperlyConfigured:
                response.status_code = 406
                template_names = [name % {'status_code': response.status_code} for name in
                                  self.exception_template_names]
                data = {}  # discard query data because I'm actually showing an error page

        context = self.resolve_context(data, request, response)
        return self._render(template_names, context, RequestContext(request), 'html')

    def _render(self, template_name, context, context_instance, response_format):
        return render_to_string(template_name, context, context_instance, response_format)


class JinjaAjaxRenderer(JinjaRenderer):
    """This is the same as the Jinja renderer, but will use the ajax rendering logic to return a partial page"""
    media_type = 'text/plain'
    format = 'ajax'

    def _render(self, template_name, context, context_instance, response_format):
        return render_to_ajax(template_name, context, context_instance)

API_RENDERERS = (JSONRenderer, BrowsableAPIRenderer)
NOAPI_RENDERERS = (JinjaRenderer, JinjaAjaxRenderer)
