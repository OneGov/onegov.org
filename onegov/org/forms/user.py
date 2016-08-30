from onegov.form import Form, merge_forms
from onegov.org import _
from onegov.user import UserCollection
from wtforms import BooleanField, RadioField, validators
from wtforms.fields.html5 import EmailField


AVAILABLE_ROLES = [
    ('admin', _("Admin")),
    ('editor', _("Editor")),
    ('member', _("Member"))
]


class ManageUserForm(Form):
    """ Defines the edit user form. """

    role = RadioField(
        label=_("Role"),
        choices=AVAILABLE_ROLES,
        default='member'
    )

    active = BooleanField(_("Active"), default=True)


class PartialNewUserForm(Form):
    """ Defines parts of the new user form not found in the manage user form.

    """

    username = EmailField(
        label=_("E-Mail"),
        description=_("The users e-mail address (a.k.a. username)"),
        validators=[validators.InputRequired(), validators.Email()]
    )

    def validate_username(self, field):
        users = UserCollection(self.request.app.session())

        if users.by_username(field.data):
            raise validators.ValidationError(
                _("A user with this e-mail address exists already"))


NewUserForm = merge_forms(PartialNewUserForm, ManageUserForm)
