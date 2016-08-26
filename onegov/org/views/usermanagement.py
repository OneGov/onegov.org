from collections import defaultdict

from onegov.core.security import Secret
from onegov.org import _, OrgApp
from onegov.org.layout import DefaultLayout
from onegov.user import User, UserCollection


@OrgApp.html(model=UserCollection, template='usermanagement.pt',
             permission=Secret)
def view_usermanagement(self, request):
    """ Allows the management of organisation users. """

    layout = DefaultLayout(self, request)

    users = defaultdict(list)

    for user in self.query().order_by(User.username).all():
        users[user.role].append(user)

    return {
        'layout': layout,
        'title': _("Usermanagement"),
        'users': users
    }
