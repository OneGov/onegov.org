from onegov.chat import Message, MessageCollection
from onegov.core.templates import render_macro
from onegov.core.layout import ChameleonLayout
from onegov.ticket import Ticket


class MacroRenderedMessage(Message):

    def get(self, request):
        layout = ChameleonLayout(self, request)
        return render_macro(
            macro=layout.macros['message_{}'.format(self.type)],
            request=request,
            content={
                'layout': layout,
                'model': self
            }
        )


class TicketChangeMessage(MacroRenderedMessage):

    __mapper_args__ = {
        'polymorphic_identity': 'ticket_change'
    }

    @classmethod
    def create(cls, ticket, request, change):
        messages = MessageCollection(
            request.app.session(), type='ticket_change')

        return messages.add(
            channel_id=ticket.number,
            owner=request.current_username,
            meta={
                'id': ticket.id.hex,
                'handler_code': ticket.handler_code,
                'change': change,
                'group': ticket.group
            }
        )

    def link(self, request):
        return request.class_link(Ticket, {
            'id': self.meta['id'],
            'handler_code': self.meta['handler_code'],
        })
