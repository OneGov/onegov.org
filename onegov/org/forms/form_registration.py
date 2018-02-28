from onegov.form import Form
from onegov.org import _
from wtforms.fields import BooleanField, RadioField
from wtforms.fields.html5 import DateField, IntegerField
from wtforms.validators import NumberRange, InputRequired


class FormRegistrationWindowForm(Form):
    """ Form to edit registration windows. """

    start = DateField(
        label=_("Start"),
        validators=[InputRequired()]
    )

    end = DateField(
        label=_("End"),
        validators=[InputRequired()]
    )

    limit_attendees = RadioField(
        label=_("Limit the number of attendees"),
        fieldset=_("Attendees"),
        choices=[
            ('yes', _("Yes, limit the number of attendees")),
            ('no', _("No, allow an unlimited number of attendees"))
        ],
        default='yes'
    )

    limit = IntegerField(
        label=_("Number of attendees"),
        fieldset=_("Attendees"),
        depends_on=('limit_attendees', 'yes'),
        validators=(NumberRange(min=1, max=None), )
    )

    waitinglist = RadioField(
        label=_("Waitinglist"),
        fieldset=_("Attendees"),
        depends_on=('limit_attendees', 'yes'),
        choices=[
            ('yes', _("Yes, allow for more submissions than available spots")),
            ('no', _("No, ensure that all submissions can be accepted"))
        ],
        default='yes'
    )

    stop = BooleanField(
        label=_("Do not accept any submissions"),
        fieldset=_("Advanced"),
        default=False
    )

    def process_obj(self, obj):
        super().process_obj(obj)
        self.waitinglist.data = obj.overflow and 'yes' or 'no'
        self.limit_attendees.data = obj.limit and 'yes' or 'no'
        self.limit.data = obj.limit or ''
        self.stop.data = obj.enabled

    def populate_obj(self, obj, *args, **kwargs):
        super().populate_obj(obj, *args, **kwargs)
        obj.overflow = self.waitinglist.data == 'yes'
        obj.limit = self.limit_attendees.data == 'yes' and self.limit.data or 0
        obj.enabled = not self.stop.data
