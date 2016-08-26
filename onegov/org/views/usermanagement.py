import morepath

from collections import defaultdict
from onegov.core.security import Secret
from onegov.org import _, OrgApp
from onegov.org.elements import Link
from onegov.org.forms import ManageUserForm
from onegov.org.layout import UserManagementLayout
from onegov.user import User, UserCollection


@OrgApp.html(model=UserCollection, template='usermanagement.pt',
             permission=Secret)
def view_usermanagement(self, request):
    """ Allows the management of organisation users. """

    layout = UserManagementLayout(self, request)

    users = defaultdict(list)

    for user in self.query().order_by(User.username).all():
        users[user.role].append(user)

    return {
        'layout': layout,
        'title': _("User Management"),
        'users': users
    }


@OrgApp.form(model=User, template='form.pt', form=ManageUserForm,
             permission=Secret)
def handle_manage_user(self, request, form):

    if form.submitted(request):
        form.populate_obj(self)
        request.success(_("Your changes were saved"))

        return morepath.redirect(request.class_link(UserCollection))
    else:
        form.process(obj=self)

    layout = UserManagementLayout(self, request)
    layout.breadcrumbs.append(Link(self.username, '#'))

    return {
        'layout': layout,
        'title': self.username,
        'form': form
    }
