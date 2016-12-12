from anaf.test import AnafTestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User as DjangoUser
from anaf.core.models import Group, Perspective, ModuleSetting
from forms import FilterForm, ProjectForm
from models import Project, Milestone, Task, TaskStatus, TaskTimeSlot
from anaf.identities.models import Contact, ContactType
from datetime import datetime, timedelta
from freezegun import freeze_time


class ProjectsModelsTest(AnafTestCase):
    """ Documents models tests"""
    def setUp(self):
        self.project = Project(name='test')
        self.project.save()

        self.taskstatus = TaskStatus(name='test')
        self.taskstatus.save()

        self.task = Task(name='test', project=self.project, status=self.taskstatus)
        self.task.save()

    def test_task_priority_human(self):
        """Default priority should be 3, text representation should be 'Normal'
        """
        self.assertEqual(self.task.priority, 3)
        self.assertEqual(self.task.priority_human(), 'Normal')

    def test_get_estimated_time_default(self):
        """Default estimated time is None, string representation is empty string """
        self.assertIsNone(self.task.estimated_time)
        self.assertEqual(self.task.get_estimated_time(), '')

    def test_get_estimated_time_one_min(self):
        self.task.estimated_time = 1
        self.assertEqual(self.task.get_estimated_time(), ' 1 minutes')

    def test_get_estimated_time_zero_min(self):
        self.task.estimated_time = 0
        self.assertEqual(self.task.get_estimated_time(), 'Less than 1 minute')

    def test_get_estimated_time_60_min(self):
        self.task.estimated_time = 60
        self.assertEqual(self.task.get_estimated_time(), ' 1 hours ')

    def test_get_estimated_time_61_min(self):
        self.task.estimated_time = 61
        self.assertEqual(self.task.get_estimated_time(), ' 1 hours  1 minutes')

    def test_model_task_get_absolute_url(self):
        self.task.get_absolute_url()

    # def test_save TODO: save is overridden and has some extra logic

    def test_get_absolute_url(self):
        """Test if get_absolute_url works without raising any exception"""
        self.project.get_absolute_url()

    def add_time_slot(self, total_time):
        duser, created = DjangoUser.objects.get_or_create(username='testuser')
        time_from = datetime(year=2015, month=8, day=3)
        time_to = time_from + total_time
        timeslot = TaskTimeSlot(task=self.task, user=duser.profile, time_from=time_from, time_to=time_to)
        timeslot.save()

    def test_get_total_time_default(self):
        self.assertEqual(self.task.get_total_time(), timedelta())

    def test_get_total_time_with_timeslots1(self):
        total_time = timedelta(hours=3)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time(), total_time)

    def test_get_total_time_tuple_default(self):
        self.assertIsNone(self.task.get_total_time_tuple())

    def test_get_total_time_tuple(self):
        total_time = timedelta(hours=3)
        self.add_time_slot(total_time)
        h, m, s = self.task.get_total_time_tuple()
        self.assertEqual((h, m, s), (3, 0, 0))

    def test_get_total_time_string_default(self):
        self.assertEqual(self.task.get_total_time_string(), '0 minutes')

    def test_get_total_time_string_one_min(self):
        total_time = timedelta(minutes=1)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time_string(), ' 1 minutes')

    def test_get_total_time_string_zero_min(self):
        total_time = timedelta(minutes=0)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time_string(), '0 minutes')

    def test_get_total_time_string_30_secs(self):
        total_time = timedelta(seconds=30)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time_string(), 'Less than 1 minute')

    def test_get_total_time_string_60_min(self):
        total_time = timedelta(minutes=60)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time_string(), ' 1 hours ')

    def test_get_total_time_string_61_min(self):
        total_time = timedelta(minutes=61)
        self.add_time_slot(total_time)
        self.assertEqual(self.task.get_total_time_string(), ' 1 hours  1 minutes')

    def test_is_being_done_by(self):
        duser, created = DjangoUser.objects.get_or_create(username='testuser')
        self.assertFalse(self.task.is_being_done_by(duser.profile))

        time_from = datetime(year=2015, month=8, day=3)
        timeslot = TaskTimeSlot(task=self.task, user=duser.profile, time_from=time_from)
        timeslot.save()
        self.task.save()

        self.assertTrue(self.task.is_being_done_by(duser.profile))

    def test_model_task_status(self):
        """Test task status"""
        obj = TaskStatus(name='test')
        obj.save()
        self.assertEquals('test', obj.name)
        self.assertNotEquals(obj.id, None)
        obj.get_absolute_url()
        obj.delete()

    def test_model_milestone(self):
        tstatus = TaskStatus(name='test')
        tstatus.save()
        mstone = Milestone(project=self.project, status=tstatus)
        mstone.save()
        mstone.get_absolute_url()


class TestModelTaskTimeSlot(AnafTestCase):
    username = "testuser"
    password = "password"

    def setUp(self):
        self.group, created = Group.objects.get_or_create(name='test_group')
        self.user, created = DjangoUser.objects.get_or_create(username=self.username)
        self.user.set_password(self.password)
        self.user.save()

        self.project = Project(name='test')
        self.project.save()

        self.taskstatus = TaskStatus(name='test')
        self.taskstatus.save()

        self.task = Task(name='test', project=self.project, status=self.taskstatus)
        self.task.save()

        self.time_from = datetime(year=2015, month=8, day=3)
        self.total_time = timedelta(minutes=61)
        self.time_to = self.time_from + self.total_time
        self.timeslot = TaskTimeSlot(task=self.task, user=self.user.profile, time_from=self.time_from,
                                     time_to=self.time_to)
        self.timeslot.save()

    def test_get_absolute_url(self):
        self.timeslot.get_absolute_url()

    def test_get_time_secs(self):
        with freeze_time(datetime(year=2015, month=8, day=4)):
            self.assertEqual(self.timeslot.get_time_secs(), 86400)

    def test_get_time(self):
        """A time slot without a time from or time to will return a delta of 0"""
        timeslot2 = TaskTimeSlot(task=self.task, user=self.user.profile, time_from=self.time_from)
        timeslot3 = TaskTimeSlot(task=self.task, user=self.user.profile, time_to=self.time_to)
        self.assertEqual(timeslot2.get_time(), timedelta(0))
        self.assertEqual(timeslot3.get_time(), timedelta(0))
        self.assertEqual(self.timeslot.get_time(), self.total_time)

    def test_get_time_tuple(self):
        h, m, s = self.timeslot.get_time_tuple()
        self.assertEqual((h, m, s), (1, 1, 0))
        timeslot2 = TaskTimeSlot(task=self.task, user=self.user.profile, time_to=self.time_to)
        self.assertIsNone(timeslot2.get_time_tuple())

    def test_get_time_string(self):
        self.assertEqual(self.timeslot.get_time_string(), ' 1 hours  1 minutes')

        total_time = timedelta(minutes=1)
        self.timeslot.time_to = self.time_from + total_time
        self.assertEqual(self.timeslot.get_time_string(), ' 1 minutes')

        # if it has a timedelta of zero it will use now-time_from
        total_time = timedelta(minutes=0)
        self.timeslot.time_to = self.time_from + total_time
        with freeze_time(datetime(year=2015, month=8, day=4)):
            self.assertEqual(self.timeslot.get_time_string(), '24 hours ')

        total_time = timedelta(seconds=30)
        self.timeslot.time_to = self.time_from + total_time
        self.assertEqual(self.timeslot.get_time_string(), 'Less than 1 minute')

        total_time = timedelta(minutes=60)
        self.timeslot.time_to = self.time_from + total_time
        self.assertEqual(self.timeslot.get_time_string(), ' 1 hours ')

        self.timeslot.time_from = None
        self.assertEqual(self.timeslot.get_time_string(), '')

        self.timeslot.time_from = self.time_from
        self.timeslot.time_to = None
        with freeze_time(datetime(year=2015, month=8, day=4)):
            self.assertEqual(self.timeslot.get_time_string(), '24 hours ')

    def test_is_open(self):
        # a time slot with both time_from and time_to means it is closed
        self.assertFalse(self.timeslot.is_open())
        self.timeslot.time_to = None
        self.assertTrue(self.timeslot.is_open())


class ProjectsViewsNotLoggedIn(AnafTestCase):
    """Test views Behaviour when user is not logged in
    Basically assert that all views are protected by login
    """

    def assert_protected(self, name, args=None):
        response = self.client.get(reverse(name, args=args))
        # old view redirects to login page
        if response.status_code == 302:
            self.assertRedirects(response, reverse('user_login'))
        else:
            # DRF based view returns 401 unauthorized
            self.assertEqual(response.status_code, 401)

    def test_index(self):
        self.assert_protected('project-list')

    def test_index_owned(self):
        self.assert_protected('task-owned')

    def test_index_assigned(self):
        self.assert_protected('task-assigned')

    def test_index_by_status(self):
        self.assert_protected('task-status', (1,))

    def test_index_in_progress(self):
        self.assert_protected('task-in-progress')

    def test_project_add(self):
        self.assert_protected('project-new')

    def test_project_add_typed(self):
        self.assert_protected('project-new-to-project', (1,))

    def test_project_view(self):
        self.assert_protected('project-detail', (1, ))

    def test_project_edit(self):
        self.assert_protected('project-edit', (1, ))

    def test_project_delete(self):
        self.assert_protected('project-delete', (1, ))

    def test_milestone_add(self):
        self.assert_protected('milestone-new')

    def test_milestone_add_typed(self):
        self.assert_protected('milestone-new-to-project', (1, ))

    def test_milestone_view(self):
        self.assert_protected('milestone-detail', (1, ))

    def test_milestone_edit(self):
        self.assert_protected('milestone-edit', (1, ))

    def test_milestone_delete(self):
        self.assert_protected('milestone-delete', (1, ))

    def test_milestone_set_status(self):
        self.assert_protected('milestone-set-status', (1, 1))

    def test_task_add(self):
        self.assert_protected('task-new')

    def test_task_add_typed(self):
        self.assert_protected('task-new-to-project', (1,))

    def test_task_add_to_milestone(self):
        self.assert_protected('task-new-to-milestone', (1,))

    def test_task_add_subtask(self):
        self.assert_protected('task-new-subtask', (1,))

    def test_task_view(self):
        self.assert_protected('task-detail', (1,))

    def test_task_edit(self):
        self.assert_protected('task-edit', (1,))

    def test_task_delete(self):
        self.assert_protected('task-delete', (1,))

    def test_task_set_status(self):
        self.assert_protected('task-set-status', (1, 1))

    def test_task_time_slot_start(self):
        self.assert_protected('task-start', (1,))

    def test_task_time_slot_stop(self):
        self.assert_protected('tasktimeslot-stop', (1,))

    def test_task_time_slot_add(self):
        self.assert_protected('tasktimeslot-new-to-task', (1,))

    def test_task_time_slot_view(self):
        self.assert_protected('tasktimeslot-detail', (1,))

    def test_task_time_slot_edit(self):
        self.assert_protected('tasktimeslot-edit', (1,))

    def test_task_time_slot_delete(self):
        self.assert_protected('tasktimeslot-delete', (1,))

    def test_task_status_add(self):
        self.assert_protected('taskstatus-new')

    def test_task_status_edit(self):
        self.assert_protected('projects_task_status_edit', (1,))

    def test_task_status_delete(self):
        self.assert_protected('projects_task_status_delete', (1,))

    def test_settings_view(self):
        self.assert_protected('projects_settings_view')

    def test_settings_edit(self):
        self.assert_protected('projects_settings_edit')

    def test_ajax_task_lookup(self):
        self.assert_protected('projects_ajax_task_lookup')

    def test_gantt_view(self):
        self.assert_protected('project-gantt', (1,))


class ProjectsViewsTest(AnafTestCase):
    username = "test"
    password = "password"

    def setUp(self):
        self.group, created = Group.objects.get_or_create(name='test')
        self.user, created = DjangoUser.objects.get_or_create(username=self.username, is_staff=True)
        self.user.set_password(self.password)
        self.user.save()
        perspective, created = Perspective.objects.get_or_create(name='default')
        perspective.set_default_user()
        perspective.save()

        ModuleSetting.set('default_perspective', perspective.id)

        self.contact_type = ContactType(name='test')
        self.contact_type.set_default_user()
        self.contact_type.save()

        self.contact = Contact(name='test', contact_type=self.contact_type)
        self.contact.related_user = self.user.profile
        self.contact.set_default_user()
        self.contact.save()

        self.project = Project(name='test', manager=self.contact, client=self.contact)
        self.project.set_default_user()
        self.project.save()

        self.status = TaskStatus(name='test')
        self.status.set_default_user()
        self.status.save()

        self.status2 = TaskStatus(name='second status')
        self.status2.set_default_user()
        self.status2.save()

        self.milestone = Milestone(name='test', project=self.project, status=self.status)
        self.milestone.set_default_user()
        self.milestone.save()

        self.task = Task(name='test', project=self.project, status=self.status, caller=self.contact)
        self.task.set_default_user()
        self.task.save()

        self.task_assigned = Task(name='test', project=self.project, status=self.status)
        self.task_assigned.save()
        self.task_assigned.assigned.add(self.user.profile)

        self.time_slot = TaskTimeSlot(task=self.task, details='test', time_from=datetime.now(), user=self.user.profile)
        self.time_slot.set_default_user()
        self.time_slot.save()

        self.parent = Project(name='test')
        self.parent.set_default_user()
        self.parent.save()

        self.parent_task = Task(name='test', project=self.project, status=self.status, priority=3)
        self.parent_task.set_default_user()
        self.parent_task.save()

        self.client = Client()

        self.client.login(username=self.username, password=self.password)

    def test_index(self):
        """Test project index page with login at /projects/"""
        response = self.client.get(reverse('project-list'))
        self.assertEquals(response.status_code, 200)

    def assertQuerysetEqual(self, qs, values, transform=repr, ordered=True, msg=None):
        return super(ProjectsViewsTest, self).assertQuerysetEqual(qs, map(repr, values), transform, ordered, msg)

    def test_index_owned(self):
        """Test owned tasks page at /task/owned/"""
        response = self.client.get(reverse('task-owned'))
        self.assertEquals(response.status_code, 200)
        self.assertQuerysetEqual(response.context['tasks'], [self.task])
        self.assertEqual(type(response.context['filters']), FilterForm)
        # todo: actually test the form generated, if it has the right fields and querysets
        # self.assertEqual(str(response.context['filters']), str(filterform))

    def test_index_assigned(self):
        """Test assigned tasks page at /task/assigned/"""
        response = self.client.get(reverse('task-assigned'))
        self.assertEquals(response.status_code, 200)
        self.assertQuerysetEqual(response.context['tasks'], [self.task_assigned])
        self.assertEqual(type(response.context['filters']), FilterForm)

    # Projects
    def test_project_add(self):
        """Test index page with login at /projects/add/"""
        response = self.client.get(reverse('project-new'))
        self.assertEquals(response.status_code, 200)
        self.assertEqual(type(response.context['form']), ProjectForm)

        projects_qty = Project.objects.count()
        form_params = {'name': 'project_name', 'details': 'new project details'}
        response = self.client.post(reverse('project-new'), data=form_params)
        self.assertEquals(response.status_code, 302)
        project_id = response['Location'].split('/')[-2]
        project_id = int(project_id)  # make sure it got a number for project id
        self.assertRedirects(response, reverse('project-detail', args=[project_id]))
        self.assertEqual(Project.objects.count(), projects_qty+1)
        project = Project.objects.get(id=project_id)
        self.assertEqual(project.name, form_params['name'])
        self.assertEqual(project.details, form_params['details'])

    def test_project_add_typed(self):
        """Test index page with login at /projects/add/<project_id>/"""
        response = self.client.get(reverse('project-new-to-project', args=[self.parent.id]))
        self.assertEquals(response.status_code, 200)

    def test_project_view_login(self):
        """Test index page with login at /projects/view/<project_id>"""
        response = self.client.get(reverse('project-detail', args=[self.project.id]))
        self.assertEquals(response.status_code, 200)

    def test_project_edit_login(self):
        """Test index page with login at /projects/edit//<project_id>"""
        response = self.client.get(reverse('project-edit', args=[self.project.id]))
        self.assertEquals(response.status_code, 200)

    def test_project_delete_login(self):
        """Test index page with login at /projects/delete//<project_id>"""
        response = self.client.get(reverse('project-delete', args=[self.project.id]))
        self.assertEquals(response.status_code, 200)

    # Milestones
    def test_milestone_add(self):
        """Test index page with login at /projects/milestone/new"""
        response = self.client.get(reverse('milestone-new'))
        self.assertEquals(response.status_code, 200)

    def test_milestone_new_to_project(self):
        """Test newmilestone page with login at /projects/milestone/new_to_project/<project_id>/"""
        response = self.client.get(reverse('milestone-new-to-project', args=[self.parent.id]))
        self.assertEquals(response.status_code, 200)

    def test_milestone_view_login(self):
        """Test index page with login at /projects/milestone/view/<milestone_id>"""
        response = self.client.get(reverse('milestone-detail', args=[self.milestone.id]))
        self.assertEquals(response.status_code, 200)

    def test_milestone_edit_login(self):
        """Test index page with login at /projects/milestone/edit/<milestone_id>"""
        response = self.client.get(reverse('milestone-edit', args=[self.milestone.id]))
        self.assertEquals(response.status_code, 200)

    def test_milestone_delete_login(self):
        """Test index page with login at /projects/milestone/delete/<milestone_id>"""
        response = self.client.get(reverse('milestone-delete', args=[self.milestone.id]))
        self.assertEquals(response.status_code, 200)

    def test_milestone_set_status_login(self):
        self.assertEqual(self.milestone.status_id, self.status.id)
        response = self.client.get(reverse('milestone-set-status', args=[self.milestone.id, self.status2.id]))
        self.assertEquals(response.status_code, 200)
        milestone = Milestone.objects.get(id=self.milestone.id)
        self.assertEqual(milestone.status_id, self.status2.id)

    # Tasks
    def test_task_add(self):
        """Test index page with login at /projects/task/new/"""
        response = self.client.get(reverse('task-new'))
        self.assertEquals(response.status_code, 200)

    def test_task_add_typed(self):
        """Test index page with login at /projects/task/add/<project_id>"""
        response = self.client.get(reverse('task-new-to-project', args=[self.project.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_add_to_milestone(self):
        """Test new task to milestone page with login at /projects/task/new_to_milestone/<milestone_id>/"""
        response = self.client.get(reverse('task-new-to-milestone', args=[self.milestone.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_add_subtask(self):
        """Test index page with login at /projects/task/add/<task_id>/"""
        response = self.client.get(reverse('task-new-subtask', args=[self.parent_task.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_set_status(self):
        """Test set status page with login at /projects/task/set/<task_id>/status/<status_id>"""
        # no format specified
        response = self.client.get(reverse('task-set-status', args=[self.task.id, self.status2.id]))
        self.assertEquals(response.status_code, 200)
        # check if status was changed on DB
        self.assertEqual(Task.objects.get(id=self.task.id).status_id, self.status2.id)
        # html
        response = self.client.get(reverse('task-set-status', args=[self.task.id, self.status.id, 'html']))
        self.assertEquals(response.status_code, 200)
        # check if status was changed on DB
        self.assertEqual(Task.objects.get(id=self.task.id).status_id, self.status.id)
        # json
        response = self.client.get(reverse('task-set-status', args=[self.task.id, self.status2.id, 'json']))
        self.assertEquals(response.status_code, 406)
        # check if status was not changed on DB
        self.assertEqual(Task.objects.get(id=self.task.id).status_id, self.status.id)

    def test_task_start(self):
        # creates empty task and makes sure it creates a time slot for the task
        task = Task(name='task 2', project=self.project, status=self.status, caller=self.contact)
        task.set_default_user()
        task.save()
        self.assertFalse(task.tasktimeslot_set.all().count())
        response = self.client.post(reverse('task-start', args=(task.id, )))
        self.assertRedirects(response, reverse('task-detail', args=[task.id]))
        self.assertEqual(task.tasktimeslot_set.all().count(), 1)  # assert that only one time slot was created
        timeslot = task.tasktimeslot_set.all()[0]
        self.assertTrue(timeslot.is_open())  # assert that timeslot correctly calculates that it is open
        self.assertTrue(task.is_being_done_by(self.user.profile))

    def test_task_start2(self):
        # start a task which has already started
        self.assertTrue(self.task.is_being_done_by(self.user.profile))
        self.assertEqual(self.task.tasktimeslot_set.all().count(), 1)  # makes sure that the task has only one timeslot
        timeslot = self.task.tasktimeslot_set.all()[0]
        self.assertTrue(timeslot.is_open())

        response = self.client.post(reverse('task-start', args=(self.task.id,)))
        self.assertRedirects(response, reverse('task-detail', args=[self.task.id]))
        self.assertEqual(self.task.tasktimeslot_set.all().count(), 1)  # assert that it didn't create another timeslot

    def test_task_start_fails_on_get(self):
        # task start shouldn't allow GET requests
        task = Task(name='task 2', project=self.project, status=self.status, caller=self.contact)
        task.set_default_user()
        task.save()
        response = self.client.get(reverse('task-start', args=(task.id,)))
        self.assertEquals(response.status_code, 405)
        response = self.client.get(reverse('task-start', args=(self.task.id,)))
        self.assertEquals(response.status_code, 405)

    def test_task_stop(self):
        self.assertTrue(self.time_slot.is_open())
        self.assertIsNone(self.time_slot.time_to)
        response = self.client.post(reverse('tasktimeslot-stop', args=(self.time_slot.id,)))
        self.assertRedirects(response, reverse('task-detail', args=[self.task.id]))
        self.time_slot = TaskTimeSlot.objects.get(id=self.time_slot.id)
        self.assertFalse(self.time_slot.is_open())
        self.assertIsNotNone(self.time_slot.time_to)

        response = self.client.get(reverse('tasktimeslot-stop', args=(self.time_slot.id,)))
        self.assertEquals(response.status_code, 405)

    def test_task_view_login(self):
        """Test index page with login at /projects/task/view/<task_id>"""
        response = self.client.get(reverse('task-detail', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_edit_login(self):
        """Test index page with login at /projects/task/edit/<task_id>"""
        response = self.client.get(reverse('task-edit', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_delete_login(self):
        """Test index page with login at /projects/task/delete/<task_id>"""
        response = self.client.get(reverse('task-delete', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    # Task Time Slots
    def test_time_slot_add(self):
        """Test index page with login at /projects/task/view/time/<task_id>add/"""
        response = self.client.get(reverse('tasktimeslot-new-to-task', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    def test_time_slot_view_login(self):
        """Test index page with login at /projects/task/view/time/<time_slot_id>"""
        response = self.client.get(reverse('task-detail', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    def test_time_slot_edit_login(self):
        """Test index page with login at /projects/task/edit/time/<time_slot_id>"""
        response = self.client.get(reverse('task-edit', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    def test_time_slot_delete_login(self):
        """Test index page with login at /projects/task/delete/time/<time_slot_id>"""
        response = self.client.get(reverse('task-delete', args=[self.task.id]))
        self.assertEquals(response.status_code, 200)

    # Task Statuses
    def test_task_status_add(self):
        """Test index page with login at /projects/task/status/add/"""
        response = self.client.get(reverse('taskstatus-new'))
        self.assertEquals(response.status_code, 200)

    def test_task_status_view_login(self):
        """Test index page with login at /projects/task/status/view/<status_id>/"""
        response = self.client.get(reverse('task-status', args=[self.status.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_status_edit_login(self):
        """Test index page with login at /projects/task/status/edit/<status_id>/"""
        response = self.client.get(reverse('projects_task_status_edit', args=[self.status.id]))
        self.assertEquals(response.status_code, 200)

    def test_task_status_delete_login(self):
        """Test index page with login at /projects/task/status/delete/<status_id>/"""
        response = self.client.get(reverse('projects_task_status_delete', args=[self.status.id]))
        self.assertEquals(response.status_code, 200)

    # Settings

    def test_project_settings_view(self):
        """Test index page with login at /projects/settings/view/"""
        response = self.client.get(reverse('projects_settings_view'))
        self.assertEquals(response.status_code, 200)

    def test_project_settings_edit(self):
        """Test index page with login at /projects/settings/edit/"""
        response = self.client.get(reverse('projects_settings_edit'))
        self.assertEquals(response.status_code, 200)
