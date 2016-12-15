"""
Reports module views
"""
from __future__ import unicode_literals
from itertools import groupby
from datetime import datetime
import json
import re
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.db.models import Q
from anaf.core.conf import settings
from anaf.core.views import user_denied
from anaf.core.models import Object, Module
from anaf.core.rendering import render_to_response
from anaf.core.decorators import mylogin_required, handle_response_format
from anaf.reports.forms import ObjChoiceForm, MassActionForm, ChartForm, FilterForm
from anaf.reports.models import Report, Field, Model, Chart
from anaf.reports.helpers import dumps, loads, aggregate_functions, number_field_regex


def _get_default_context(request):
    """Returns default context as a dict()"""

    massform = MassActionForm(request.user.profile)

    context = {'massform': massform}

    return context


def _process_mass_form(f):
    """Pre-process request to handle mass action form for Reports"""

    def wrap(request, *args, **kwargs):
        user = request.user.profile
        if 'massform' in request.POST:
            for key in request.POST:
                if 'mass-report' in key:
                    try:
                        report = Report.objects.get(pk=request.POST[key])
                        form = MassActionForm(
                            user, request.POST, instance=report)
                        if form.is_valid() and user.has_permission(report, mode='w'):
                            form.save()
                    except Exception:
                        pass

        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__

    return wrap


def _get_objects():
    object_types = Object.objects.all().values(
        'object_type').distinct().order_by('object_type')
    # TODO: filter these
    object_names = ["({0!s})  {1!s}".format(object_types[i]['object_type'].split('.')[1].title(),
                     Object.objects.filter(
                         object_type=object_types[i]['object_type'])
                     .order_by()[0].get_human_type())
                    for i in range(0, len(object_types))]
    return object_types, object_names


def _get_module_name(path):
    """"
    Returns real and translated module name for the given path, e.g. Service
    Support for anaf.services.models.Ticket
    """
    modulename = path
    try:
        modulepath = re.match("(?P<modulepath>.*)\.models.(?P<name>\w+)$", path).group('modulepath')
        module = Module.objects.get(name=modulepath)
        modulename = _(module.title)
    except Module.DoesNotExist:
        pass
    except AttributeError:
        pass
    return modulename

#
# Charts
#


def _get_chart_ajax(request, chart_id=None, div_id=None):
    """For AJAX"""
    "Reports index page"

    options = json.dumps({
        'chart': {'renderTo': div_id,
                  'defaultSeriesType': 'line'
                  },
        'title': {'text': 'Alexs Quest for Mooshoo'
                  },
        'xAxis': {
            'categories': ['Apples', 'Bananas', 'Oranges']
        },
        'yAxis': {
            'title': {
                'text': 'Howdy'
            }
        },

        'series': [{'name': 'hi', 'data': 50},
                   {'name': 'h0', 'data': 60},
                   {'name': 'hi', 'data': 50},
                   {'name': 'h0', 'data': 10},
                   {'name': 'hi', 'data': 80},
                   {'name': 'h0', 'data': 40},
                   {'name': 'hi', 'data': 50},
                   {'name': 'h0', 'data': 26},
                   {'name': 'hi', 'data': 50},
                   {'name': 'h0', 'data': 20},
                   {'name': 'hi', 'data': 30},
                   {'name': 'h0', 'data': 80},
                   {'name': 'hi', 'data': 50}]
    })

    return HttpResponse(options, content_type=settings.ANAF_RESPONSE_FORMATS['json'])


def _get_report_content(report, request=None):
    model = loads(report.model)

    obj = model.name
    obj = obj.split('.')

    module_name = obj[0] + '.' + obj[1] + '.' + obj[2]
    import_name = obj[3]

    module = __import__(module_name, globals(), locals(), [import_name], -1)
    classobj = getattr(module, import_name)

    if request:
        unfiltered_set = Object.filter_by_request(request, classobj.objects)
    else:
        unfiltered_set = classobj.objects.exclude(trash=True)

    # construct filter
    filters = {}
    excludes = {}
    for field in model.fields:
        for filt in field.filters:
            if filt['operand'] == 'is':
                filters.setdefault(field.name + '__in', []).append(filt['choice'])
            elif filt['operand'] == 'not':
                excludes.setdefault(field.name + '__in', []).append(filt['choice'])
            elif filt['operand'] == 'beforedate':
                filters[field.name + '__gte'] = datetime.date(datetime.strptime(filt['choice'], '%m/%d/%Y'))
            elif filt['operand'] == 'afterdate':
                filters[field.name + '__lte'] = datetime.date(datetime.strptime(filt['choice'], '%m/%d/%Y'))
            elif filt['operand'] == 'beforedatetime':
                filters[field.name + '__gte'] = datetime.strptime(filt['choice'], '%m/%d/%Y %H:%M')
            elif filt['operand'] == 'afterdatetime':
                filters[field.name + '__lte'] = datetime.strptime(filt['choice'], '%m/%d/%Y %H:%M')
            elif filt['operand'] == 'on':
                filters.setdefault(field.name + '__in', []).append(datetime.strptime(filt['choice'], '%m/%d/%Y'))

    set = unfiltered_set.filter(**filters).exclude(**excludes)

    # Check for group
    groupname = None
    groups = None
    for field in model.fields:
        if field.groupby == 1:
            groupname = field.name

    if groupname:
        xfield = classobj._meta.get_field_by_name(groupname)[0]
        xtype = xfield.get_internal_type()
        if xtype == 'ManyToManyField':
            set = sorted(set, key=lambda item: (
                ", ".join([str(i) for i in getattr(item, groupname).all()])), reverse=True)
            groups, groupnames = [], []
            for obj in set:
                for n in getattr(obj, groupname).all():
                    if n not in groupnames:
                        groupnames.append(n)
            for n in groupnames:
                l = []
                for obj in set:
                    if n in getattr(obj, groupname).all():
                        l.append(obj)
                groups.append((str(n), l))

        elif xtype == ('DateTimeField' or 'DateField'):
            set = set.order_by(groupname)
            #set = sorted(set, key = lambda item: getattr(item,groupname))
            # TODO: Fix this sort
            groups, groupnames, l, ng = [], [], [], []
            n = None

            if xtype == 'DateTimeField':
                def dt(ob):
                    return getattr(ob, groupname).date()
            else:
                def dt(ob):
                    return getattr(ob, groupname)

            for x in set:
                n = dt(x)
                if n:
                    break
            if n:
                for obj in set:
                    if getattr(obj, groupname):
                        if dt(obj) == n:
                            l.append(obj)
                        else:
                            groups.append((str(n), l))
                            l = []
                            n = dt(obj)
                            l.append(obj)
                    else:
                        ng.append(obj)
                if ng:
                    groups.append(('None', ng))

        else:
            set = sorted(set, key=lambda item: str(item.get_field_value(groupname)), reverse=True)
            groups = []
            for g, ks in groupby(set, key=lambda item: str(item.get_field_value(groupname))):
                groups.append((g, list(ks)))
            xfield = set[0]._meta.get_field_by_name(groupname)[0]

    # Count aggregate functions
    agg_funcs = {}
    for field in model.fields:  # get fields and aggregate functions for them
        if field.display and getattr(field, 'aggregation', None):
            xfield = classobj._meta.get_field_by_name(field.name)[0]
            if number_field_regex.match(xfield.get_internal_type()) and field.aggregation in aggregate_functions:
                agg_funcs[field.name] = aggregate_functions[
                    field.aggregation]['function']

    aggregations = {}
    if agg_funcs:
        for grouper, ls in groups if groups else (('set', set),):
            data = {}
            for s in ls:
                for key in agg_funcs:
                    data.setdefault(key, []).append(getattr(s, key, 0))
            aggrs = {}
            for key, func in agg_funcs.items():
                aggrs[key] = func(data.get(key, [0, ]))
            aggregations[grouper] = aggrs

    return {'model': model,
            'set': set,
            'groups': groups,
            'groupname': groupname,
            'aggregations': aggregations}


@mylogin_required
@handle_response_format
@_process_mass_form
def charts_index(request, response_format='html'):
    "Charts index page"

    charts = Object.filter_by_request(request, Chart.objects)

    context = _get_default_context(request)
    context.update({'charts': charts})

    return render_to_response('reports/chart_index', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def chart_add(request, report_id=None, response_format='html'):

    if request.POST:
        form = ChartForm(
            request.user.profile, request.POST, report_id=report_id)
        if form.is_valid():
            chart = form.save()
            chart.set_user_from_request(request)
            return HttpResponseRedirect(reverse('reports_report_view', args=[chart.report.id]))

    else:
        form = ChartForm(request.user.profile, report_id=report_id)

    context = {'form': form}

    return render_to_response('reports/chart_add', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def chart_edit(request, chart_id=None, response_format='html'):

    chart = get_object_or_404(Chart, pk=chart_id)
    report_id = chart.report.id

    if request.POST:
        form = ChartForm(
            request.user.profile, request.POST, chart_id=chart_id)
        if form.is_valid():
            chart = form.save()
            chart.set_user_from_request(request)
            return HttpResponseRedirect(reverse('reports_report_view', args=[report_id]))

    else:
        form = ChartForm(request.user.profile, chart_id=chart_id)

    context = {
        'chart': chart,
        'form': form}

    return render_to_response('reports/chart_edit', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def chart_view(request, chart_id=None, response_format='html'):

    chart = get_object_or_404(Chart, pk=chart_id)

    context = {'chart': chart}

    return render_to_response('reports/chart_view', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def chart_delete(request, chart_id, response_format='html'):
    "Chart delete"

    chart = get_object_or_404(Chart, pk=chart_id)
    report = chart.report
    if not request.user.profile.has_permission(chart, mode='w'):
        return user_denied(request, message="You don't have access to this Event")

    if request.POST:
        if 'delete' in request.POST:
            if 'trash' in request.POST:
                chart.trash = True
                chart.save()
            else:
                chart.delete()
            return HttpResponseRedirect(reverse('reports_report_view',
                                                args=[report.id]))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('reports_report_view',
                                                args=[report.id]))

    return render_to_response('reports/chart_delete',
                              {'chart': chart},
                              context_instance=RequestContext(request), response_format=response_format)


#
# Index pages
#
@mylogin_required
@handle_response_format
@_process_mass_form
def index(request, response_format='html'):
    "Reports index page"

    reports = Object.filter_by_request(request, Report.objects)
    context = _get_default_context(request)
    context.update({'reports': reports})

    return render_to_response('reports/index', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
@_process_mass_form
def index_owned(request, response_format='html'):
    "Reports owned by user"

    reports = Object.filter_by_request(
        request, Report.objects.filter(creator=request.user.profile))

    context = _get_default_context(request)
    context.update({'reports': reports})

    return render_to_response('reports/index_owned', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def report_add(request, response_format='html'):
    """Create new report based on user choice"""
    if 'report' in request.POST:
        report_id = request.POST['report']
        return HttpResponseRedirect(reverse('reports_report_edit', args=[report_id]))
    # FIRST TIME AN OBJECT IS CHOSEN
    if 'choice' in request.POST:
        form = None
        obj = request.POST['choice']
        obj = str(obj.replace("{'object_type': u'", '').replace("'}", ''))
        full_object = obj
        obj = obj.split('.', 3)

        module_name = obj[0] + '.' + obj[1] + '.' + obj[2]
        import_name = obj[3]

        module = __import__(
            module_name, globals(), locals(), [import_name], -1)
        classobj = getattr(module, import_name)

        obj = classobj()
        names = obj.get_field_names()

        fields = []
        for name in names:
            fields.append(Field(name=name, display=True))

        model = Model(full_object, fields)

        report = Report()
        report.name = "Untitled {0!s} Report".format((obj._meta.object_name))
        report.model = dumps(model)
        report.creator = request.user.profile
        report.save()

        return HttpResponseRedirect(reverse('reports_report_edit', args=[report.id]))

    # Initial Object Type Choice
    user_modules = [mod.name for mod in request.user.profile.get_perspective().get_modules()]
    modules = [mod.name for mod in Module.objects.all()]

    query = Q(object_type__contains="core")
    for module in modules:
        if module not in user_modules:
            query = query | Q(object_type__contains=module)

    object_types = list(Object.objects.all().exclude(query).values(
        'object_type').distinct().order_by('object_type'))

    object_names = []
    for object_type in object_types:
        module_name = _get_module_name(object_type['object_type'])
        human_type = Object.objects.filter(
            object_type=object_type['object_type'])[0].get_human_type()

        object_names.append("{0!s}: {1!s}".format(module_name, human_type))

    form = ObjChoiceForm(request.user, object_types=object_types, object_names=object_names)

    return render_to_response('reports/report_add', {'form': form}, context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def report_edit(request, report_id=None, response_format='html'):
    """Create new report based on user choice"""
    report = get_object_or_404(Report, pk=report_id)

    if not request.user.profile.has_permission(report, mode='w'):
        return user_denied(request, message="You don't have access to edit this Report")
    model = loads(report.model)

    if request.POST and 'commit' in request.POST:
        # UPDATE MODEL
        if 'report_name' in request.POST:
            report.name = request.POST['report_name']
        fieldnames = []
        aggregations = {}
        for key in request.POST:
            if 'field' in key:
                fieldnames.append(request.POST[key])
            elif 'aggregation-' in key:
                aggregations[key[12:]] = request.POST[key]

        for field in model.fields:
            field.aggregation = aggregations.get(field.name)
            if field.name in fieldnames:
                field.display = True
            else:
                field.display = False

        report.model = dumps(model)
        report.save()

    if 'commit' in request.POST:
        return HttpResponseRedirect(reverse('reports_report_view', args=[report.id]))

    return render_to_response('reports/report_edit',
                              {'report': report,
                               'model': model,
                               },
                              context_instance=RequestContext(request),
                              response_format=response_format)


#
# Aggregations, Filters, Joins and Grouping
#
@mylogin_required
@handle_response_format
def report_filter(request, report_id, field_name, response_format='html'):
    """View to Filter over a given field for a Report"""

    report = get_object_or_404(Report, pk=report_id)
    if not request.user.profile.has_permission(report, mode='w'):
        return user_denied(request, message="You don't have access to this Report")

    if request.POST:
        FilterForm(request.user.profile, request.POST,
                   report=report, field_name=field_name).save()
        return HttpResponseRedirect(reverse('reports_report_edit', args=[report.id]))

    else:
        form = FilterForm(
            request.user.profile, report=report, field_name=field_name)

    return render_to_response('reports/report_filter',
                              {'form': form,
                               'field_name': field_name},

                              context_instance=RequestContext(request), response_format=response_format)


@mylogin_required
@handle_response_format
def report_filter_remove(request, report_id, field_name, filter_index, response_format='html'):
    """Remove a Filter on a given field for a Report"""

    report = get_object_or_404(Report, pk=report_id)
    if not request.user.profile.has_permission(report, mode='w'):
        return user_denied(request, message="You don't have write access to this Report")

    model = loads(report.model)
    field = model.get_field(field_name)
    field.filters.pop(int(filter_index) - 1)
    report.model = dumps(model)
    report.save()

    return HttpResponseRedirect(reverse('reports_report_edit', args=[int(report_id)]))


@mylogin_required
@handle_response_format
def report_group(request, report_id, field_name, response_format='html'):
    """View to Group by a given field in a report"""

    t = get_object_or_404(Report, pk=report_id)
    if not request.user.profile.has_permission(t, mode='w'):
        return user_denied(request, message="You don't have access to this Report")

    model = loads(t.model)

    # Check if this field is already grouped, if so then remove grouping
    thisfield = model.get_field(field_name)
    if thisfield.groupby == 1:
        thisfield.groupby = 0
    else:
        # Other wise reset grouping and set selected field as groupfield
        for field in model.fields:
            field.groupby = 0

        field = model.get_field(field_name)
        field.groupby = 1

    t.model = dumps(model)
    t.save()

    return report_edit(request, report_id=report_id, response_format=response_format)

#
# Reports
#


@mylogin_required
@handle_response_format
def report_view(request, response_format='html', report_id=None):
    """Display the report"""

    report = get_object_or_404(Report, pk=report_id)
    report_context = _get_report_content(report, request)
    context = _get_default_context(request)
    context.update(report_context)

    if response_format == "csv":
        return render_to_response('reports/gen', context,
                                  context_instance=RequestContext(request),
                                  response_format='csv')

    report_content = str(render_to_response('reports/gen', context,
                                            context_instance=RequestContext(
                                                request),
                                            response_format='html')).replace('Content-Type: text/html', '')

    charts = report.chart_set.filter(trash=False)

    # Now take the rendered report and embed it in the report view page.
    context = _get_default_context(request)
    context.update({'report': report,
                    'charts': charts,
                    'report_content': report_content})

    return render_to_response('reports/report_view', context,
                              context_instance=RequestContext(request),
                              response_format=response_format)


@mylogin_required
@handle_response_format
def report_delete(request, report_id, response_format='html'):
    "Report delete"

    report = get_object_or_404(Report, pk=report_id)
    if not request.user.profile.has_permission(report, mode='w'):
        return user_denied(request, message="You don't have access to this Event")

    if request.POST:
        if 'delete' in request.POST:
            if 'trash' in request.POST:
                report.trash = True
                report.save()
            else:
                report.delete()
            return HttpResponseRedirect(reverse('reports_index'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('reports_report_view', args=[report.id]))

    return render_to_response('reports/report_delete',
                              {'report': report},
                              context_instance=RequestContext(request), response_format=response_format)
