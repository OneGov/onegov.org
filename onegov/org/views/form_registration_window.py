from onegov.core.security import Private
from onegov.form import FormDefinition, FormRegistrationWindow
from onegov.org import OrgApp, _
from onegov.org.forms import FormRegistrationWindowForm
from onegov.org.layout import FormSubmissionLayout
from onegov.org.new_elements import Link, Confirm, Intercooler


@OrgApp.form(
    model=FormDefinition,
    name='new-registration-window',
    permission=Private,
    form=FormRegistrationWindowForm,
    template='form.pt')
def handle_new_registration_form(self, request, form):

    title = _("New Registration Window")

    layout = FormSubmissionLayout(self, request)
    layout.editbar_links = None
    layout.breadcrumbs.append(Link(title, '#'))

    if form.submitted(request):

        form.populate_obj(self.add_registration_window(
            form.start.data,
            form.end.data
        ))

        request.success(_("The registration window was added successfully"))
        return request.redirect(request.link(self))

    return {
        'layout': layout,
        'title': title,
        'form': form
    }


@OrgApp.form(
    model=FormRegistrationWindow,
    permission=Private,
    form=FormRegistrationWindowForm,
    template='form.pt')
def handle_edit_registration_form(self, request, form):

    title = _("Edit Registration Window")

    layout = FormSubmissionLayout(self.form, request)
    layout.editbar_links = [
        Link(
            text=_("Delete"),
            url=layout.csrf_protected_url(request.link(self)),
            attrs={'class': 'delete-link'},
            traits=(
                Confirm(
                    _(
                        "Do you really want to delete "
                        "this registration window?"
                    ),
                    _("Existing submissions will be disassociated."),
                    _("Delete registration window")
                ),
                Intercooler(
                    request_method='DELETE',
                    redirect_after=request.link(self.form)
                )
            )
        )
    ]
    layout.breadcrumbs.append(Link(title, '#'))

    if form.submitted(request):
        form.populate_obj(self)

        request.success("Your changes were saved")
        return request.redirect(request.link(self.form))

    elif not request.POST:
        form.process(obj=self)

    return {
        'layout': layout,
        'title': title,
        'form': form
    }


@OrgApp.view(
    model=FormRegistrationWindow,
    permission=Private,
    request_method='DELETE')
def delete_registration_window(self, request):
    request.assert_valid_csrf_token()

    self.disassociate()
    request.session.delete(self)

    request.success(_("The registration window was deleted"))
