"""
News module forms
"""

from django import forms
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from anaf.core.conf import settings
from anaf.core.models import UpdateRecord, ModuleSetting, Object


class UpdateRecordForm(forms.ModelForm):

    """ UpdateRecord form """

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user', None)
        super(UpdateRecordForm, self).__init__(*args, **kwargs)

        self.fields['body'].required = True
        self.fields['body'].label = _("Details")

        self.fields['recipients'].help_text = ""
        self.fields['recipients'].required = False
        self.fields['recipients'].widget.attrs.update({'class': 'multicomplete',
                                                       'callback': reverse('contacts:ajax_access_lookup')})

        # get default permissions from settings
        try:
            conf = ModuleSetting.get_for_module(
                'anaf.core', 'default_permissions')[0]
            default_permissions = conf.value
        except:
            default_permissions = settings.ANAF_DEFAULT_PERMISSIONS

        if self.user and 'userallgroups' in default_permissions:
            self.fields['recipients'].initial = [
                i.id for i in self.user.other_groups.all().only('id')]
            self.fields['recipients'].initial.append(
                self.user.default_group.id)
        elif self.user and 'usergroup' in default_permissions:
            self.fields['recipients'].initial = [self.user.default_group.id]

    class Meta:

        "TaskRecordForm"
        model = UpdateRecord
        fields = ['body', 'recipients']


class UpdateRecordFilterForm(forms.ModelForm):

    """ Filter form definition """

    def __init__(self, user, *args, **kwargs):
        super(UpdateRecordFilterForm, self).__init__(*args, **kwargs)

        self.fields['author'].label = _("Author")
        self.fields['about'].label = _("About")

        self.fields['author'].required = False
        self.fields['author'].widget.attrs.update({'class': 'autocomplete',
                                                  'callback': reverse('contacts:ajax_user_lookup')})

        self.fields['about'].queryset = Object.filter_permitted(
            user, Object.objects, mode='x')
        self.fields['about'].required = False
        self.fields['about'].null = True
        self.fields['about'].help_text = ""
        self.fields['about'].widget.attrs.update({'class': 'multicomplete',
                                                  'callback': reverse('core_ajax_object_lookup')})

    class Meta:

        "Filter"
        model = UpdateRecord
        fields = ('author', 'about')
