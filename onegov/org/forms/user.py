from onegov.form import Form
from onegov.org import _
from wtforms.fields import BooleanField, RadioField


class ManageUserForm(Form):
    """ Defines the edit user form. """

    role = RadioField(
        label=_("Role"),
        choices=[
            ('admin', _("Admin")),
            ('editor', _("Editor")),
            ('member', _("Member"))
        ],
        default='member'
    )

    active = BooleanField(_("Active"))
