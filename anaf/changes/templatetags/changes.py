"""
Changes templatetags
"""
from coffin import template
from anaf.core.rendering import render_to_string
from jinja2 import contextfunction, Markup
from django.template import RequestContext

register = template.Library()


@contextfunction
def changes_set_list(context, changesets):
    """Print a list of ChangeSets"""
    request = context['request']

    response_format = 'html'
    if 'response_format' in context:
        response_format = context['response_format']

    return Markup(render_to_string('changes/tags/changeset_list',
                                   {'changesets': changesets},
                                   context_instance=RequestContext(request),
                                   response_format=response_format))

register.object(changes_set_list)
