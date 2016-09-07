from collections import namedtuple
from lxml import etree
from onegov.event import OccurrenceCollection
from onegov.newsletter import NewsletterCollection
from onegov.org import _
from onegov.org.elements import Link, LinkGroup


XSLT_BASE = """<?xml version="1.0" encoding="UTF-8"?>

    <xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:i18n="http://xml.zope.org/namespaces/i18n"
    xmlns:metal="http://xml.zope.org/namespaces/metal"
    xmlns:tal="http://xml.zope.org/namespaces/tal">

    <xsl:template match="@*|node()" name="identity">
      <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
      </xsl:copy>
    </xsl:template>

    <xsl:template match="page">
      <div class="homepage">
        <xsl:apply-templates select="@*|node()"/>
      </div>
    </xsl:template>

    {}

    </xsl:stylesheet>

"""


XML_BASE = """<?xml version="1.0" encoding="UTF-8"?>

    <page xmlns:i18n="http://xml.zope.org/namespaces/i18n"
          xmlns:metal="http://xml.zope.org/namespaces/metal"
          xmlns:tal="http://xml.zope.org/namespaces/tal">

          {}

    </page>
"""

# the number of lines from the start of XML_Base to where the structure is
# injected (for correct line error reporting on the UI side)
XML_LINE_OFFSET = 6


def transform_homepage_structure(structure):
    xslt = XSLT_BASE.format('\n'.join(w.template for w in WIDGETS))
    xslt = etree.fromstring(xslt.encode('utf-8'))

    xml = XML_BASE.format(structure)
    xml = etree.fromstring(xml.encode('utf-8'))

    template = etree.XSLT(xslt)(xml)

    return etree.tostring(template, encoding='unicode', method='xml')


class Widget(object):

    @property
    def id(self):
        raise NotImplementedError

    @property
    def template(self):
        raise NotImplementedError

    def get_variables(self, layout):
        return {}

    def is_used(self, structure):
        return '<{}'.format(self.id) in structure


class ColumnWidget(Widget):

    id = 'column'

    template = """
        <xsl:template match="column">
            <div class="small-12 medium-{@span} columns">
                <div class="row">
                    <xsl:apply-templates select="node()"/>
                </div>
            </div>
        </xsl:template>
    """


class PanelWidget(Widget):

    id = 'panel'

    template = """
        <xsl:template match="panel">
            <div class="homepage-panel">
                <xsl:if test="@title">
                    <h2>
                        <xsl:value-of select="@title" />
                    </h2>
                </xsl:if>

                <xsl:if test="events">
                    <xsl:apply-templates select="events"/>
                </xsl:if>

                <ul class="panel-links">
                    <xsl:for-each select="link">
                    <li>
                        <a>
                            <xsl:attribute name="href">
                                <xsl:value-of select="@url" />
                            </xsl:attribute>

                            <xsl:value-of select="node()" />
                        </a>

                        <xsl:if test="@description">
                            <small>
                                <xsl:value-of select="@description" />
                            </small>
                        </xsl:if>
                    </li>
                    </xsl:for-each>
                </ul>
            </div>
        </xsl:template>
    """


class NewsWidget(Widget):

    id = 'news'

    template = """
        <xsl:template match="news">
            <div metal:use-macro="layout.macros.newslist"
                tal:define="heading 'h3'; show_all_news_link True"
            />
        </xsl:template>
    """

    def get_variables(self, layout):
        return {
            'news': layout.root_pages[-1].news_query.limit(2).all()
        }


class ContentWidget(Widget):

    id = 'homepage-content'

    template = """
        <xsl:template match="homepage-content">
            <div class="homepage-content page-text">
                <tal:block
                    content="structure layout.org.meta.get('homepage_content')"
                />
            </div>
        </xsl:template>
    """


class EventsWidget(Widget):

    id = 'events'

    template = """
        <xsl:template match="events">
            <metal:block use-macro="layout.macros['events-panel']" />
        </xsl:template>
    """

    def get_variables(self, layout):
        occurrences = OccurrenceCollection(layout.app.session()).query()
        occurrences = occurrences.limit(4)

        # XXX circular import
        from onegov.org.layout import EventBaseLayout

        event_layout = EventBaseLayout(layout.model, layout.request)
        event_links = [
            Link(
                text=o.title,
                url=layout.request.link(o),
                subtitle=event_layout.format_date(o.localized_start, 'event')
            ) for o in occurrences
        ]

        event_links.append(
            Link(
                text=_("All events"),
                url=event_layout.events_url,
                classes=('more-link', )
            )
        )

        latest_events = LinkGroup(
            title=_("Events"),
            links=event_links,
        )

        return {
            'events_panel': latest_events
        }


Tile = namedtuple('Tile', ['page', 'links', 'number'])


class TilesWidget(Widget):

    id = 'homepage-tiles'

    template = """
        <xsl:template match="homepage-tiles">
            <xsl:choose>
                <xsl:when test="@show-title">
                    <metal:block use-macro="layout.macros['homepage-tiles']"
                       tal:define="show_title True" />
                </xsl:when>
                <xsl:otherwise>
                    <metal:block use-macro="layout.macros['homepage-tiles']"
                      tal:define="show_title False" />
                </xsl:otherwise>
            </xsl:choose>
        </xsl:template>
    """

    def get_variables(self, layout):
        return {'tiles': tuple(self.get_tiles(layout))}

    def get_tiles(self, layout):
        homepage_pages = layout.request.app.homepage_pages
        request = layout.request
        link = request.link
        session = layout.app.session()
        classes = ('tile-sub-link', )

        for ix, page in enumerate(layout.root_pages):
            if page.type == 'topic':

                children = homepage_pages.get(page.id, tuple())
                children = (session.merge(c, load=False) for c in children)

                if not request.is_manager:
                    children = (
                        c for c in children if not c.is_hidden_from_public
                    )

                yield Tile(
                    page=Link(page.title, link(page)),
                    number=ix + 1,
                    links=tuple(
                        Link(c.title, link(c), classes=classes, model=c)
                        for c in children
                    )
                )
            elif page.type == 'news':
                news_url = link(page)
                years = (str(year) for year in page.years)

                links = [
                    Link(year, news_url + '?year=' + year, classes=classes)
                    for year in years
                ]

                links.append(Link(
                    _("Newsletter"), link(NewsletterCollection(session)),
                    classes=classes
                ))

                yield Tile(
                    page=Link(page.title, news_url),
                    number=ix + 1,
                    links=links
                )
            else:
                raise NotImplementedError


WIDGETS = [
    ColumnWidget(),
    PanelWidget(),
    NewsWidget(),
    ContentWidget(),
    EventsWidget(),
    TilesWidget()
]
