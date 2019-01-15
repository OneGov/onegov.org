import morepath

from libres.modules.errors import LibresError
from onegov.core.security import Public, Private
from onegov.form import merge_forms
from onegov.org import OrgApp, utils, _
from onegov.org.forms import AllocationRuleForm
from onegov.org.forms import DaypassAllocationEditForm
from onegov.org.forms import DaypassAllocationForm
from onegov.org.forms import RoomAllocationEditForm
from onegov.org.forms import RoomAllocationForm
from onegov.org.layout import AllocationEditFormLayout
from onegov.org.layout import AllocationRulesLayout
from onegov.org.layout import ResourceLayout
from onegov.org.new_elements import Link, Confirm, Intercooler
from onegov.reservation import Allocation, Resource, ResourceCollection
from purl import URL
from sqlalchemy.orm import defer, defaultload


@OrgApp.json(model=Resource, name='slots', permission=Public)
def view_allocations_json(self, request):
    """ Returns the allocations in a fullcalendar compatible events feed.

    See `<http://fullcalendar.io/docs/event_data/events_json_feed/>`_ for
    more information.

    """

    start, end = utils.parse_fullcalendar_request(request, self.timezone)

    if not (start and end):
        return tuple()

    # get all allocations (including mirrors), for the availability calculation
    query = self.scheduler.allocations_in_range(start, end, masters_only=False)
    query = query.order_by(Allocation._start)
    query = query.options(defer(Allocation.data))
    query = query.options(defer(Allocation.group))
    query = query.options(
        defaultload('reserved_slots')
        .defer('reservation_token')
        .defer('allocation_id')
        .defer('end'))

    allocations = query.all()

    # but only return the master allocations
    return tuple(
        e.as_dict() for e in utils.AllocationEventInfo.from_allocations(
            request, self.scheduler, allocations
        )
    )


@OrgApp.html(model=Resource, name='rules', permission=Private,
             template='allocation_rules.pt')
def view_allocation_rules(self, request):
    layout = AllocationRulesLayout(self, request)

    def link_for_rule(rule, name):
        url = URL(request.link(self, name='stop-rule'))
        url = url.query_param('csrf-token', layout.csrf_token)
        url = url.query_param('rule', rule['id'])

        return url.as_string()

    def actions_for_rule(rule):
        yield Link(
            text=_("Stop"),
            url=link_for_rule(rule, 'stop-rule'),
            traits=(
                Confirm(
                    _(
                        'Do you really want to stop "${title}"?',
                        mapping={'title': rule['title']}
                    ),
                    _(
                        "The rule will be removed without affecting "
                        "existing allocations."
                    ),
                    _("Stop rule")
                ),
                Intercooler(
                    request_method="POST",
                    redirect_after=request.link(self, 'rules')
                )
            )
        )

        yield Link(
            text=_("Delete"),
            url=link_for_rule(rule, 'delete-rule'),
            traits=(
                Confirm(
                    _(
                        'Do you really want to delete "${title}"?',
                        mapping={'title': rule['title']}
                    ),
                    _(
                        "All allocations created by the rule will be removed, "
                        "if they haven't been reserved yet."
                    ),
                    _("Delete rule")
                ),
                Intercooler(
                    request_method="POST",
                    redirect_after=request.link(self, 'rules')
                )
            )
        )

    def rules_with_actions():
        form_class = get_allocation_rule_form_class(self, request)

        for rule in self.content.get('rules', ()):
            form = form_class()
            form.rule = rule

            yield {
                'title': rule['title'],
                'actions': tuple(actions_for_rule(rule)),
                'form': form
            }

    return {
        'layout': layout,
        'title': _("Rules"),
        'rules': tuple(rules_with_actions())
    }


def get_new_allocation_form_class(resource, request):
    """ Returns the form class for new allocations (different resources have
    different allocation forms).

    """

    if resource.type == 'daypass':
        return DaypassAllocationForm

    if resource.type == 'room':
        return RoomAllocationForm

    raise NotImplementedError


def get_edit_allocation_form_class(allocation, request):
    """ Returns the form class for existing allocations (different resources
    have different allocation forms).

    """

    resource = ResourceCollection(
        request.app.libres_context).by_id(allocation.resource)

    if resource.type == 'daypass':
        return DaypassAllocationEditForm

    if resource.type == 'room':
        return RoomAllocationEditForm

    raise NotImplementedError


def get_allocation_rule_form_class(resource, request):
    """ Returns the form class for allocation rules. """

    form = get_new_allocation_form_class(resource, request)

    return merge_forms(AllocationRuleForm, form)


@OrgApp.form(model=Resource, template='form.pt', name='new-allocation',
             permission=Private, form=get_new_allocation_form_class)
def handle_new_allocation(self, request, form):
    """ Handles new allocations for differing form classes. """

    if form.submitted(request):
        try:
            allocations = self.scheduler.allocate(
                dates=form.dates,
                whole_day=form.whole_day,
                quota=form.quota,
                quota_limit=form.quota_limit,
                data=form.data,
                partly_available=form.partly_available
            )
        except LibresError as e:
            utils.show_libres_error(e, request)
        else:
            if not allocations:
                request.alert(_("No allocations to add"))
            else:
                request.success(
                    _("Successfully added ${n} allocations", mapping={
                        'n': len(allocations)
                    }))

                self.highlight_allocations(allocations)

                return morepath.redirect(request.link(self))

    elif not request.POST:
        start, end = utils.parse_fullcalendar_request(request, self.timezone)
        whole_day = request.params.get('whole_day') == 'yes'

        if start and end:
            if whole_day:
                form.start.data = start
                form.end.data = end

                if hasattr(form, 'as_whole_day'):
                    form.as_whole_day.data = 'yes'
            else:
                form.start.data = start
                form.end.data = end

                if hasattr(form, 'as_whole_day'):
                    form.as_whole_day.data = 'no'

                if hasattr(form, 'start_time'):
                    form.start_time.data = start
                    form.end_time.data = end

    layout = ResourceLayout(self, request)
    layout.breadcrumbs.append(Link(_("New allocation"), '#'))
    layout.editbar_links = None

    return {
        'layout': layout,
        'title': _("New allocation"),
        'form': form
    }


@OrgApp.form(model=Allocation, template='form.pt', name='edit',
             permission=Private, form=get_edit_allocation_form_class)
def handle_edit_allocation(self, request, form):
    """ Handles edit allocation for differing form classes. """

    resources = ResourceCollection(request.app.libres_context)
    resource = resources.by_id(self.resource)

    # this is a bit of a hack to keep the current view when a user drags an
    # allocation around, which opens this form and later leads back to the
    # calendar - if the user does this on the day view we want to return to
    # the same day view after the process
    # therefore we set the view on the resource (where this is okay) and on
    # the form action (where it's a bit of a hack), to ensure that the view
    # parameter is around for the whole time
    if 'view' in request.params:
        resource.view = view = request.params['view']
        form.action = URL(form.action).query_param('view', view).as_string()

    if form.submitted(request):
        new_start, new_end = form.dates

        try:
            resource.scheduler.move_allocation(
                master_id=self.id,
                new_start=new_start,
                new_end=new_end,
                new_quota=form.quota,
                quota_limit=form.quota_limit
            )
        except LibresError as e:
            utils.show_libres_error(e, request)
        else:
            request.success(_("Your changes were saved"))
            resource.highlight_allocations([self])

            return morepath.redirect(request.link(resource))
    elif not request.POST:
        form.apply_model(self)

        start, end = utils.parse_fullcalendar_request(request, self.timezone)
        if start and end:
            form.apply_dates(start, end)

    return {
        'layout': AllocationEditFormLayout(self, request),
        'title': _("Edit allocation"),
        'form': form
    }


@OrgApp.view(model=Allocation, request_method='DELETE', permission=Private)
def handle_delete_allocation(self, request):
    """ Deletes the given resource (throwing an error if there are existing
    reservations associated with it).

    """
    request.assert_valid_csrf_token()

    resource = request.app.libres_resources.by_allocation(self)
    resource.scheduler.remove_allocation(id=self.id)

    @request.after
    def trigger_calendar_update(response):
        response.headers.add('X-IC-Trigger', 'rc-allocations-changed')


@OrgApp.form(model=Resource, template='form.pt', name='new-rule',
             permission=Private, form=get_allocation_rule_form_class)
def handle_allocation_rule(self, request, form):
    layout = AllocationRulesLayout(self, request)

    if form.submitted(request):
        changes = form.apply(self)

        rules = self.content.get('rules', [])
        rules.append(form.rule)
        self.content['rules'] = rules

        request.success(_(
            "New rule active, ${n} allocations created", mapping={'n': changes}
        ))

        return request.redirect(request.link(self, name='rules'))

    return {
        'layout': layout,
        'title': _("New Rule"),
        'form': form
    }


@OrgApp.view(model=Resource, request_method='POST', permission=Private,
             name='stop-rule')
def handle_stop_rule(self, request):
    request.assert_valid_csrf_token()

    self.content['rules'] = [
        rule for rule in self.content.get('rules', ())
        if rule['id'] != request.params.get('rule', None)
    ]

    request.success(_("The rule was stopped"))
