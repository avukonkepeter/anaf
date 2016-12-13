"""
Core module views
"""

from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.sites.models import RequestSite
from django.utils.translation import ugettext as _

from anaf.core.conf import settings
from django.db.models import Q
from anaf.core.rendering import render_to_response
from anaf.core.models import User, Group, Invitation, Perspective, Module, ModuleSetting, Page, PageFolder
from forms import PerspectiveForm, UserForm, PasswordForm, \
    GroupForm, PageForm, PageFolderForm, FilterForm, SettingsForm, PERMISSION_CHOICES
from anaf.core.mail import EmailInvitation
from anaf.core.decorators import module_admin_required, mylogin_required, handle_response_format

import re
from django.utils.six import text_type as unicode


def _get_filter_query(args):
    """Creates a query to filter Modules based on FilterForm arguments"""
    query = Q(trash=False)

    for arg in args:
        if hasattr(Perspective, arg) and args[arg]:
            kwargs = {unicode(arg + '__id'): int(args[arg])}
            query = query & Q(**kwargs)

    return query


@handle_response_format
@mylogin_required
@module_admin_required()
def index_perspectives(request, response_format='html'):
    """Perspective list"""

    query = _get_filter_query(request.GET)
    perspectives = Perspective.objects.filter(query).order_by('name')

    filters = FilterForm(
        request.user.profile, 'perspective', request.GET)

    message = request.session.pop('message', '')

    return render_to_response('core/administration/index_perspectives',
                              {'perspectives': perspectives,
                               'filters': filters,
                               'message': message},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def index_modules(request, response_format='html'):
    """Module list"""
    modules = Module.objects.all().order_by('title')

    return render_to_response('core/administration/index_modules',
                              {'modules': modules},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Perspectives
#


@handle_response_format
@mylogin_required
@module_admin_required()
def perspective_view(request, perspective_id, response_format='html'):
    """Perspective view"""
    perspective = get_object_or_404(Perspective, pk=perspective_id)

    all_modules = Module.objects.all()

    message = request.session.pop('message', '')

    return render_to_response('core/administration/perspective_view',
                              {'perspective': perspective,
                               'all_modules': all_modules,
                               'message': message},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def perspective_edit(request, perspective_id, response_format='html'):
    """Perspective edit"""
    perspective = get_object_or_404(Perspective, pk=perspective_id)
    # Don't let users delete their last perspective
    other_perspectives = Perspective.objects.filter(
        trash=False).exclude(id=perspective_id)
    admin_module = Module.objects.filter(name='anaf.core')[0]

    if request.POST:
        if 'cancel' not in request.POST:
            form = PerspectiveForm(
                request.user.profile, request.POST, instance=perspective)
            if form.is_valid():
                perspective = form.save()
                modules = perspective.modules.all()
                if modules and admin_module not in modules and\
                        not other_perspectives.filter(Q(modules=admin_module) | Q(modules__isnull=True)):
                    perspective.modules.add(admin_module)
                    request.session['message'] = _(
                            "This is your only Perspective with Administration module. You would be locked out!")
                return HttpResponseRedirect(reverse('core_admin_perspective_view', args=[perspective.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_perspective_view', args=[perspective.id]))
    else:
        form = PerspectiveForm(
            request.user.profile, instance=perspective)

    request.session.pop('message', '')

    return render_to_response('core/administration/perspective_edit',
                              {'perspective': perspective,
                               'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def perspective_delete(request, perspective_id, response_format='html'):
    "Perspective delete"

    perspective = get_object_or_404(Perspective, pk=perspective_id)
    all_modules = Module.objects.all()
    message = ""

    # Don't let users delete their last perspective
    other_perspectives = Perspective.objects.filter(
        trash=False).exclude(id=perspective_id)
    admin_module = all_modules.filter(name='anaf.core')[0]
    if not other_perspectives:
        message = _("This is your only Perspective.")
    elif not other_perspectives.filter(Q(modules=admin_module) | Q(modules__isnull=True)):
        message = _(
            "This is your only Perspective with Administration module. You would be locked out!")
    else:
        if request.POST:
            if 'delete' in request.POST:
                if 'trash' in request.POST:
                    perspective.trash = True
                    perspective.save()
                else:
                    perspective.delete()
                return HttpResponseRedirect(reverse('core_admin_index_perspectives'))
            elif 'cancel' in request.POST:
                return HttpResponseRedirect(reverse('core_admin_perspective_view', args=[perspective.id]))

    return render_to_response('core/administration/perspective_delete',
                              {'perspective': perspective,
                               'all_modules': all_modules,
                               'message': message},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def perspective_add(request, response_format='html'):
    "Perspective add"

    if request.POST:
        if 'cancel' not in request.POST:
            perspective = Perspective()
            form = PerspectiveForm(
                request.user.profile, request.POST, instance=perspective)
            if form.is_valid():
                perspective = form.save()
                perspective.set_user_from_request(request)
                return HttpResponseRedirect(reverse('core_admin_perspective_view', args=[perspective.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_index_perspectives'))
    else:
        form = PerspectiveForm(request.user.profile)

    return render_to_response('core/administration/perspective_add',
                              {'form': form.as_ul()},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Modules
#


@handle_response_format
@mylogin_required
@module_admin_required()
def module_view(request, module_id, response_format='html'):
    "Module view"
    module = get_object_or_404(Module, pk=module_id)

    return render_to_response('core/administration/module_view',
                              {'module': module},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Users
#


@handle_response_format
@mylogin_required
@module_admin_required()
def index_users(request, response_format='html'):
    "User List"

    users = User.objects.order_by('user__username')

    return render_to_response('core/administration/index_users',
                              {'users': users},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def user_view(request, user_id, response_format='html'):
    "User view"

    profile = get_object_or_404(User, pk=user_id)
    try:
        contacts = profile.contact_set.exclude(trash=True)
    except:
        contacts = []

    modules = profile.get_perspective().get_modules()

    return render_to_response('core/administration/user_view',
                              {'profile': profile, 'contacts': contacts,
                                  'modules': modules},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def user_edit(request, user_id, response_format='html'):
    "User edit"

    profile = get_object_or_404(User, pk=user_id)
    if request.POST:
        if 'cancel' not in request.POST:
            form = UserForm(request.POST, instance=profile)
            if form.is_valid():
                profile = form.save()
                return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))
    else:
        form = UserForm(instance=profile)

    return render_to_response('core/administration/user_edit',
                              {'profile': profile,
                               'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
def user_password(request, user_id, response_format='html'):
    "User change password form"

    profile = get_object_or_404(User, pk=user_id)
    if request.POST:
        if 'cancel' not in request.POST:
            form = PasswordForm(profile.user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))
    else:
        form = PasswordForm(profile.user)

    return render_to_response('core/administration/user_password',
                              {'profile': profile, 'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def user_delete(request, user_id, response_format='html'):
    "User delete"

    profile = get_object_or_404(User, pk=user_id)
    message = ""

    if profile == request.user.profile:
        message = _("This is you!")
    else:
        if request.POST:
            if 'delete' in request.POST:
                profile.delete()
                return HttpResponseRedirect(reverse('core_admin_index_users'))
            elif 'cancel' in request.POST:
                return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))

    return render_to_response('core/administration/user_delete',
                              {'profile': profile,
                               'message': message},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def user_add(request, response_format='html'):
    "User add"

    user_limit = settings.ANAF_SUBSCRIPTION_USER_LIMIT

    if user_limit > 0:
        user_number = User.objects.filter(disabled=False).count()
        if user_number >= user_limit:
            return HttpResponseRedirect(reverse('core_billing_upgrade'))

    if request.POST:
        if 'cancel' not in request.POST:
            form = UserForm(request.POST)
            if form.is_valid():
                profile = form.save()
                return HttpResponseRedirect(reverse('core_admin_user_view', args=[profile.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_index_users'))
    else:
        form = UserForm()

    return render_to_response('core/administration/user_add',
                              {'form': form},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Invites
#


@handle_response_format
@mylogin_required
@module_admin_required()
def user_invite(request, emails=None, response_format='html'):
    "Invite people to Anaf"

    user_limit = settings.ANAF_SUBSCRIPTION_USER_LIMIT

    # Check whether any invites can be made at all
    if user_limit > 0:
        user_number = User.objects.filter(disabled=False).count()
        invites_left = user_limit - user_number
        if user_number >= user_limit:
            return HttpResponseRedirect(reverse('core_billing_upgrade'))
    else:
        invites_left = 100000000000000

    invited = []
    if request.POST or emails:
        sender = request.user.profile
        default_group = sender.default_group
        domain = RequestSite(request).domain
        if not emails:
            emails = request.POST.get('emails').split(',')

        # Check whether the number of invites + current users exceeds the limit
        if user_limit > 0:
            user_number = User.objects.filter(disabled=False).count()
            if len(emails) + user_number > user_limit:
                return HttpResponseRedirect(reverse('core_billing_upgrade'))

        for email in emails:
            email = email.strip()
            if len(email) > 7 and re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) is not None:
                if 0 < user_limit <= user_number:
                    break
                invitation = Invitation(
                    sender=request.user.profile, email=email, default_group=default_group)
                invitation.save()
                EmailInvitation(
                    invitation=invitation, sender=sender, domain=domain).send_email()
                invited.append(email)

    return render_to_response('core/administration/user_invite',
                              {'user_limit': user_limit,
                               'emails': emails,
                               'invites_left': invites_left,
                               'invited': invited},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Groups
#


@handle_response_format
@mylogin_required
@module_admin_required()
def index_groups(request, response_format='html'):
    "Group List"

    groups = Group.objects.order_by('parent', 'name')

    return render_to_response('core/administration/index_groups',
                              {'groups': groups},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def group_view(request, group_id, response_format='html'):
    "Group view"

    group = get_object_or_404(Group, pk=group_id)
    members = User.objects.filter(
        Q(default_group=group) | Q(other_groups=group)).distinct()
    subgroups = Group.objects.filter(parent=group)

    return render_to_response('core/administration/group_view',
                              {'group': group,
                               'subgroups': subgroups,
                               'members': members},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def group_edit(request, group_id, response_format='html'):
    "Group edit"

    group = get_object_or_404(Group, pk=group_id)

    if request.POST:
        if 'cancel' not in request.POST:
            form = GroupForm(request.POST, instance=group)
            if form.is_valid():
                group = form.save()
                return HttpResponseRedirect(reverse('core_admin_group_view', args=[group.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_group_view', args=[group.id]))
    else:
        form = GroupForm(instance=group)

    return render_to_response('core/administration/group_edit',
                              {'group': group,
                               'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def group_delete(request, group_id, response_format='html'):
    "Group delete"

    group = get_object_or_404(Group, pk=group_id)
    members = User.objects.filter(
        Q(default_group=group) | Q(other_groups=group)).distinct()
    subgroups = Group.objects.filter(parent=group)

    if request.POST:
        if 'delete' in request.POST:
            group.delete()
            return HttpResponseRedirect(reverse('core_admin_index_groups'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('core_admin_group_view', args=[group.id]))

    return render_to_response('core/administration/group_delete',
                              {'group': group,
                               'members': members,
                               'subgroups': subgroups},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def group_add(request, response_format='html'):
    "Group add"

    if request.POST:
        if 'cancel' not in request.POST:
            form = GroupForm(request.POST)
            if form.is_valid():
                group = form.save()
                return HttpResponseRedirect(reverse('core_admin_group_view', args=[group.id]))
        else:
            return HttpResponseRedirect(reverse('core_admin_index_groups'))

    else:
        form = GroupForm()

    return render_to_response('core/administration/group_add',
                              {'form': form},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Pages
#


@handle_response_format
@mylogin_required
@module_admin_required()
def index_pages(request, response_format='html'):
    "Static Pages list"
    pages = Page.objects.all().order_by('name')
    folders = PageFolder.objects.all().order_by('name')

    return render_to_response('core/administration/index_pages',
                              {'pages': pages, 'folders': folders},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def pagefolder_view(request, folder_id, response_format='html'):
    "Folder for Static Pages view"

    folder = get_object_or_404(PageFolder, pk=folder_id)
    pages = Page.objects.filter(folder=folder).order_by('name')

    return render_to_response('core/administration/pagefolder_view',
                              {'folder': folder, 'pages': pages},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def pagefolder_edit(request, folder_id, response_format='html'):
    "Folder for Static Pages edit"

    folder = get_object_or_404(PageFolder, pk=folder_id)
    if request.POST:
        form = PageFolderForm(request.POST, instance=folder)
        if form.is_valid():
            folder = form.save()
            return HttpResponseRedirect(reverse('core_admin_pagefolder_view', args=[folder.id]))
    else:
        form = PageFolderForm(instance=folder)

    return render_to_response('core/administration/pagefolder_edit',
                              {'folder': folder, 'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def pagefolder_delete(request, folder_id, response_format='html'):
    "Folder for Static Pages delete"

    folder = get_object_or_404(PageFolder, pk=folder_id)
    pages = Page.objects.filter(folder=folder).order_by('name')
    if request.POST:
        if 'delete' in request.POST:
            folder.delete()
            return HttpResponseRedirect(reverse('core_admin_index_pages'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('core_admin_pagefolder_view', args=[folder.id]))

    return render_to_response('core/administration/pagefolder_delete',
                              {'folder': folder, 'pages': pages},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def pagefolder_add(request, response_format='html'):
    "Folder for Static Pages add"

    if request.POST:
        form = PageFolderForm(request.POST)
        if form.is_valid():
            folder = form.save()
            return HttpResponseRedirect(reverse('core_admin_pagefolder_view', args=[folder.id]))
    else:
        form = PageFolderForm()

    return render_to_response('core/administration/pagefolder_add',
                              {'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@mylogin_required
@module_admin_required()
def page_view(request, page_id, response_format='html'):
    "Static Page view"
    page = get_object_or_404(Page, pk=page_id)

    return render_to_response('core/administration/page_view',
                              {'page': page},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def page_edit(request, page_id, response_format='html'):
    "Static Page edit"

    page = get_object_or_404(Page, pk=page_id)
    if request.POST:
        form = PageForm(request.POST, instance=page)
        if form.is_valid():
            page = form.save()
            return HttpResponseRedirect(reverse('core_admin_page_view', args=[page.id]))
    else:
        form = PageForm(instance=page)

    return render_to_response('core/administration/page_edit',
                              {'page': page, 'form': form},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def page_delete(request, page_id, response_format='html'):
    "Static Page delete"

    page = get_object_or_404(Page, pk=page_id)
    if request.POST:
        if 'delete' in request.POST:
            page.delete()
            return HttpResponseRedirect(reverse('core_admin_index_pages'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('core_admin_page_view', args=[page.id]))

    return render_to_response('core/administration/page_delete',
                              {'page': page},
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def page_add(request, response_format='html'):
    "Static Page add"

    if request.POST:
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save()
            return HttpResponseRedirect(reverse('core_admin_page_view', args=[page.id]))
    else:
        form = PageForm()

    return render_to_response('core/administration/page_add',
                              {'form': form},
                              context_instance=RequestContext(request), response_format=response_format)

#
# Setup Guide
#


@mylogin_required
@module_admin_required()
def setup(request, response_format='html'):
    "Quick set-up page"

    modules = Module.objects.all()

    for module in modules:
        if module.name in ('anaf.projects', 'anaf.sales', 'anaf.services'):
            module.major = True
        else:
            module.major = False

    context = {'modules': modules}

    return render_to_response('core/administration/setup', context,
                              context_instance=RequestContext(request), response_format=response_format)


#
# Settings
#
@handle_response_format
@mylogin_required
@module_admin_required()
def settings_view(request, response_format='html'):
    "Settings view"

    # default permissions
    try:
        conf = ModuleSetting.get_for_module(
            'anaf.core', 'default_permissions')[0]
        default_permissions = conf.value
    except:
        default_permissions = settings.ANAF_DEFAULT_PERMISSIONS

    default_permissions_display = default_permissions
    for key, value in PERMISSION_CHOICES:
        if key == default_permissions:
            default_permissions_display = _(value)

    # default perspective
    try:
        conf = ModuleSetting.get_for_module(
            'anaf.core', 'default_perspective')[0]
        default_perspective = Perspective.objects.get(pk=long(conf.value))
    except:
        default_perspective = None

    # language
    language = settings.ANAF_LANGUAGES_DEFAULT
    try:
        conf = ModuleSetting.get_for_module('anaf.core', 'language')[0]
        language = conf.value
    except IndexError:
        pass
    all_languages = settings.ANAF_LANGUAGES

    logopath = ''
    try:
        conf = ModuleSetting.get_for_module('anaf.core', 'logopath')[0]
        logopath = conf.value
        match = re.match('.*[a-z0-9]{32}__(?P<filename>.+)$', logopath)
        if match:
            logopath = match.group('filename')
    except:
        pass

    # time zone
    default_timezone = settings.ANAF_SERVER_DEFAULT_TIMEZONE
    try:
        conf = ModuleSetting.get_for_module(
            'anaf.core', 'default_timezone')[0]
        default_timezone = conf.value
    except Exception:
        default_timezone = settings.ANAF_SERVER_TIMEZONE[default_timezone][0]
    all_timezones = settings.ANAF_SERVER_TIMEZONE

    return render_to_response('core/administration/settings_view',
                              {
                                  'default_permissions': default_permissions,
                                  'default_permissions_display': default_permissions_display,
                                  'default_perspective': default_perspective,
                                  'language': language,
                                  'all_languages': all_languages,
                                  'logopath': logopath,
                                  'default_timezone': default_timezone,
                                  'all_timezones': all_timezones
                              },
                              context_instance=RequestContext(request), response_format=response_format)


@handle_response_format
@mylogin_required
@module_admin_required()
def settings_edit(request, response_format='html'):
    "Settings edit"

    if request.POST:
        if 'cancel' not in request.POST:
            form = SettingsForm(
                request.user.profile, request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(reverse('core_settings_view'))
        else:
            return HttpResponseRedirect(reverse('core_settings_view'))

    else:
        form = SettingsForm(request.user.profile)

    return render_to_response('core/administration/settings_edit',
                              {
                                  'form': form,
                              },
                              context_instance=RequestContext(request), response_format=response_format)
