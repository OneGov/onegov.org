from lxml import etree


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


class HeadingWidget(object):

    template = """
        <xsl:template match="heading">
            <h2>
                <xsl:apply-templates select="node()|@*"/>
            </h2>
        </xsl:template>
    """


class ColumnWidget(object):

    template = """
        <xsl:template match="column">
            <div class="small-12 medium-{@span} columns">
                <div class="row">
                    <xsl:apply-templates select="node()"/>
                </div>
            </div>
        </xsl:template>
    """


class PanelWidget(object):

    template = """
        <xsl:template match="panel">
            <div class="homepage-links-panel">
                <h2>
                    <xsl:value-of select="@title" />
                </h2>
                <ul>
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


class NewsWidget(object):

    template = """
        <xsl:template match="news">
            <tal:block metal:use-macro="layout.macros.newswidget" />
        </xsl:template>
    """


WIDGETS = [HeadingWidget(), ColumnWidget(), PanelWidget(), NewsWidget()]
