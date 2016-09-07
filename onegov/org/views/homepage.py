""" The onegov organisation homepage. """

from onegov.core.security import Public
from onegov.org import OrgApp
from onegov.org.homepage_widgets import WIDGETS
from onegov.org.layout import DefaultLayout
from onegov.org.models import Organisation


@OrgApp.html(model=Organisation, template='homepage.pt', permission=Public)
def view_org(self, request):
    """ Renders the org's homepage. """

    layout = DefaultLayout(self, request)

    default = {
        'layout': layout,
        'title': self.name
    }

    structure = self.meta.get('homepage_structure')

    if structure:
        used_widgets = (w for w in WIDGETS if w.is_used(structure))

    for widget in used_widgets:
        default.update(widget.get_variables(layout))

    return default
