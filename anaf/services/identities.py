"""
Handle objects from this module relevant to a Contact or a User
"""
from copy import deepcopy

from anaf.core.models import Object
from anaf.services.models import Ticket
from anaf.services.templatetags.services import services_ticket_list

CONTACT_OBJECTS = {'ticket_set': {'label': 'Tickets',
                                  'objects': [],
                                  'templatetag': services_ticket_list},
                   'client_sla': {'label': 'Service Level Agreements',
                                  'objects': [],
                                  'templatetag': None}, 'provider_sla': {'label': 'Provided SLAs',
                                                                         'objects': [],
                                                                         'templatetag': None}}

USER_OBJECTS = {'serviceagent_set': {'label': 'Assigned Tickets',
                                     'objects': [],
                                     'templatetag': services_ticket_list}}


def get_contact_objects(current_user, contact):
    """
    Returns a dictionary with keys specified as contact attributes
    and values as dictionaries with labels and set of relevant objects.
    """
    objects = deepcopy(CONTACT_OBJECTS)

    for key in objects:
        if hasattr(contact, key):
            manager = getattr(contact, key)
            try:
                manager = manager.filter(status__hidden=False)
            except:
                pass
            objects[key]['objects'] = Object.filter_permitted(
                current_user, manager)

    return objects


def get_user_objects(current_user, user):
    """
    Returns a dictionary with keys specified as contact attributes
    and values as dictionaries with labels and set of relevant objects.
    """

    objects = deepcopy(CONTACT_OBJECTS)

    for key in objects:
        if hasattr(user, key):
            if key == 'serviceagent_set':
                manager = Ticket.objects.filter(assigned__related_user=user)
            else:
                manager = getattr(user, key)
            if hasattr(manager, 'status'):
                manager = manager.filter(status__hidden=False)
            objects[key]['objects'] = Object.filter_permitted(
                current_user, manager)

    return objects
