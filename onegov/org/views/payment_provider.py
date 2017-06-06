import morepath

from onegov.core.security import Public, Secret
from onegov.org import _
from onegov.org.app import OrgApp
from onegov.org.layout import PaymentProviderLayout
from onegov.org.new_elements import Link, Confirm, Intercooler
from onegov.pay import PaymentProvider
from onegov.pay import PaymentProviderCollection
from onegov.pay.models.payment_providers import StripeConnect
from purl import URL


@OrgApp.html(
    model=PaymentProviderCollection,
    permission=Secret,
    template='payment_providers.pt')
def view_payment_providers(self, request):

    layout = PaymentProviderLayout(self, request)

    def links(provider):
        if not provider.default:
            yield Link(
                _("As default"),
                request.link(provider, 'default'),
                traits=(
                    Confirm(
                        _("Should this provider really be the new default?"),
                        _("All future payments will be switched."),
                        _("Make Default"), _("Cancel")
                    ),
                    Intercooler(
                        request_method='POST',
                        redirect_after=request.link(self)
                    )
                )
            )
        yield Link(
            _("Delete"),
            layout.csrf_protected_url(request.link(provider)),
            traits=(
                Confirm(
                    _("Do you really want to delete this provider?"),
                    _("This cannot be undone."),
                    _("Delete"), _("Cancel")
                ),
                Intercooler(
                    request_method='DELETE',
                    target='#' + provider.id.hex,
                    redirect_after=request.link(self)
                )
            )
        )

    return {
        'layout': layout,
        'links': links,
        'providers': tuple(self.query().order_by(PaymentProvider.created)),
        'title': _("Payment Provider"),
    }


@OrgApp.view(
    model=PaymentProviderCollection,
    name='stripe-connect-oauth',
    permission=Public)
def new_stripe_connect_provider(self, request):

    # since the csrf token salt is different for unauthenticated requests
    # we need to specify a constant one here
    # this means that any user could in theory get this token and then bypass
    # our csrf protection. However that person would have to have an admin
    # account on the same physical server (which limits the attack-surface)
    salt = 'stripe-connect-oauth'

    payment = StripeConnect(
        **request.app.payment_provider_defaults['stripe_connect'])

    if request.is_admin and 'csrf-token' not in request.params:
        handler = URL(request.url)
        handler = handler.query_param(
            'csrf-token', request.new_csrf_token(salt=salt))
        handler = handler.as_string()

        org = request.app.org

        return morepath.redirect(payment.prepare_oauth_request(
            handler,
            success_url=request.link(self, 'stripe-connect-oauth-success'),
            error_url=request.link(self, 'stripe-connect-oauth-error'),
            user_fields={
                'email': org.reply_to,
                'url': request.link(org),
                'country': 'CH',
                'business_name': org.name,
                'currency': 'CHF'
            }
        ))

    # we got a response from stripe!
    request.assert_valid_csrf_token(salt=salt)
    payment.process_oauth_response(request.params)

    # it's possible to add the same payment twice, in which case we update the
    # data of the existing payment
    for other in self.query().filter_by(type=payment.type):
        if payment.identity == other.identity:
            other.data = payment.data
            return

    # if this is the first account, it should be the default
    if not self.query().count():
        payment.default = True

    request.app.session().add(payment)


@OrgApp.view(
    model=PaymentProviderCollection,
    name='stripe-connect-oauth-success',
    permission=Secret)
def new_stripe_connection_success(self, request):
    request.success(_("Your Stripe account was connected successfully."))
    return morepath.redirect(request.link(self))


@OrgApp.view(
    model=PaymentProviderCollection,
    name='stripe-connect-oauth-error',
    permission=Secret)
def new_stripe_connection_error(self, request):
    request.success(_("Your Stripe account could not be connected."))
    return morepath.redirect(request.link(self))


@OrgApp.view(
    model=PaymentProvider,
    name='default',
    permission=Secret,
    request_method='POST')
def handle_default_provider(self, request):
    providers = PaymentProviderCollection(request.app.session())
    providers.as_default(self)

    request.success(_("Changed the default payment provider."))


@OrgApp.view(
    model=PaymentProvider,
    permission=Secret,
    request_method='DELETE')
def delete_provider(self, request):
    request.assert_valid_csrf_token()

    providers = PaymentProviderCollection(request.app.session())
    providers.delete(self)

    request.success(_("The payment provider was deleted."))