from collections import namedtuple
from onegov.core.security import Public, Private, Secret
from onegov.core.utils import render_file
from onegov.directory import Directory
from onegov.directory import DirectoryCollection
from onegov.directory import DirectoryEntry
from onegov.directory import DirectoryEntryCollection
from onegov.directory import DirectoryZipArchive
from onegov.org import OrgApp, _
from onegov.org.forms import DirectoryForm, DirectoryImportForm
from onegov.org.forms.generic import ExportForm
from onegov.org.layout import DirectoryCollectionLayout
from onegov.org.layout import DirectoryEntryCollectionLayout
from onegov.org.layout import DirectoryEntryLayout
from onegov.org.models import ExtendedDirectory, ExtendedDirectoryEntry
from onegov.org.new_elements import Link
from purl import URL
from sqlalchemy import cast
from sqlalchemy import JSON
from tempfile import NamedTemporaryFile


def get_directory_form_class(model, request):
    return ExtendedDirectory().with_content_extensions(DirectoryForm, request)


def get_directory_entry_form_class(model, request):
    form_class = ExtendedDirectoryEntry().with_content_extensions(
        model.directory.form_class, request)

    class OptionalMapForm(form_class):
        def on_request(self):
            if not model.directory.enable_map:
                self.delete_field('coordinates')

    return OptionalMapForm


@OrgApp.html(
    model=DirectoryCollection,
    template='directories.pt',
    permission=Public)
def view_directories(self, request):
    return {
        'title': _("Directories"),
        'layout': DirectoryCollectionLayout(self, request),
        'directories': request.exclude_invisible(self.query()),
        'link': lambda directory: request.link(
            DirectoryEntryCollection(directory)
        )
    }


@OrgApp.view(
    model=Directory,
    permission=Public)
def view_directory_redirect(self, request):
    return request.redirect(request.class_link(
        DirectoryEntryCollection, {'directory_name': self.name}
    ))


@OrgApp.form(model=DirectoryCollection, name='new', template='form.pt',
             permission=Secret, form=get_directory_form_class)
def handle_new_directory(self, request, form):
    if form.submitted(request):
        directory = self.add(
            title=form.title.data,
            lead=form.lead.data,
            structure=form.structure.data,
            configuration=form.configuration
        )

        request.success(_("Added a new directory"))
        return request.redirect(
            request.link(DirectoryEntryCollection(directory)))

    layout = DirectoryCollectionLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Directories"), request.link(self)),
        Link(_("New"), request.link(self, name='new'))
    ]

    return {
        'layout': layout,
        'title': _("New Directory"),
        'form': form,
        'form_width': 'large',
    }


@OrgApp.form(model=DirectoryEntryCollection, name='edit',
             template='directory_entry_form.pt', permission=Secret,
             form=get_directory_form_class)
def handle_edit_directory(self, request, form):
    migration = None

    if form.submitted(request):
        save_changes = True

        if self.directory.entries:
            migration = self.directory.migration(
                form.structure.data,
                form.configuration
            )

            if migration.changes:
                if not migration.possible:
                    save_changes = False
                    request.alert(_(
                        "The requested change cannot be performed, "
                        "as it is incompatible with existing entries"
                    ))
                else:
                    if not request.params.get('confirm'):
                        form.action += '&confirm=1'
                        save_changes = False

        if save_changes:
            form.populate_obj(self.directory)
            request.success(_("Your changes were saved"))
            return request.redirect(request.link(self))

    elif not request.POST:
        form.process(obj=self.directory)

    layout = DirectoryCollectionLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Directories"), request.link(self)),
        Link(_(self.directory.title), request.link(self)),
        Link(_("Edit"), '#')
    ]

    return {
        'layout': layout,
        'title': self.directory.title,
        'form': form,
        'form_width': 'large',
        'migration': migration,
        'model': self
    }


@OrgApp.view(
    model=DirectoryEntryCollection,
    permission=Secret,
    request_method='DELETE')
def delete_directory(self, request):
    request.assert_valid_csrf_token()

    session = request.app.session()

    for entry in self.directory.entries:
        session.delete(entry)

    DirectoryCollection(session).delete(self.directory)
    request.success(_("The directory was deleted"))


@OrgApp.html(
    model=DirectoryEntryCollection,
    permission=Public,
    template='directory.pt')
def view_directory(self, request):

    Filter = namedtuple('Filter', ('title', 'tags'))
    filters = []
    empty = tuple()

    for keyword, title, values in self.available_filters:
        filters.append(Filter(title=title, tags=tuple(
            Link(
                text=value,
                active=value in self.keywords.get(keyword, empty),
                url=request.link(self.for_filter(**{keyword: value}))
            ) for value in values
        )))

    return {
        'layout': DirectoryEntryCollectionLayout(self, request),
        'title': self.directory.title,
        'entries': request.exclude_invisible(self.query()),
        'directory': self.directory,
        'filters': filters,
        'geojson': request.link(self, name='+geojson')
    }


@OrgApp.json(
    model=DirectoryEntryCollection,
    permission=Public,
    name='geojson')
def view_geojson(self, request):
    q = self.query()
    q = q.with_entities(
        DirectoryEntry.id,
        DirectoryEntry.name,
        DirectoryEntry.title,
        DirectoryEntry.lead,
        cast(DirectoryEntry.content, JSON)["coordinates"].label('coordinates')
    )

    url_prefix = request.class_link(DirectoryEntry, {
        'directory_name': self.directory.name,
        'name': ''
    })

    return tuple({
        'type': "Feature",
        'properties': {
            'name': e.name,
            'title': e.title,
            'lead': e.lead,
            'link': url_prefix + e.name
        },
        'geometry': {
            'coordinates': [e.coordinates['lon'], e.coordinates['lat']],
            'type': "Point"
        }
    } for e in q if e.coordinates)


@OrgApp.form(
    model=DirectoryEntryCollection,
    permission=Private,
    template='form.pt',
    form=get_directory_entry_form_class,
    name='new')
def handle_new_directory_entry(self, request, form):
    if form.submitted(request):
        entry = self.directory.add_by_form(form, type='extended')

        request.success(_("Added a new directory entry"))
        return request.redirect(request.link(entry))

    layout = DirectoryEntryCollectionLayout(self, request)
    layout.breadcrumbs.append(Link(_("New"), '#'))
    layout.editbar_links = []

    return {
        'layout': layout,
        'title': _("New Directory Entry"),
        'form': form,
    }


@OrgApp.form(
    model=DirectoryEntry,
    permission=Private,
    template='form.pt',
    form=get_directory_entry_form_class,
    name='edit')
def handle_edit_directory_entry(self, request, form):
    if form.submitted(request):
        form.populate_obj(self)

        request.success(_("Your changes were saved"))
        return request.redirect(request.link(self))
    elif not request.POST:
        form.process(obj=self)

    layout = DirectoryEntryLayout(self, request)
    layout.breadcrumbs.append(Link(_("Edit"), '#'))
    layout.editbar_links = []

    return {
        'layout': layout,
        'title': self.title,
        'form': form,
    }


@OrgApp.html(
    model=DirectoryEntry,
    permission=Public,
    template='directory_entry.pt')
def view_directory_entry(self, request):

    return {
        'layout': DirectoryEntryLayout(self, request),
        'title': self.title,
        'entry': self
    }


@OrgApp.view(
    model=DirectoryEntry,
    permission=Private,
    request_method='DELETE')
def delete_directory_entry(self, request):
    request.assert_valid_csrf_token()

    session = request.app.session()
    session.delete(self)

    request.success(_("The entry was deleted"))


@OrgApp.form(model=DirectoryEntryCollection, permission=Private, name='export',
             template='export.pt', form=ExportForm)
def view_export(self, request, form):

    layout = DirectoryEntryCollectionLayout(self, request)
    layout.breadcrumbs.append(Link(_("Export"), '#'))
    layout.editbar_links = None

    if form.submitted(request):
        url = URL(request.link(self, '+zip'))
        url = url.query_param('format', form.format)

        return request.redirect(url.as_string())

    return {
        'layout': layout,
        'title': _("Export"),
        'form': form,
        'explanation': _(
            "Exports all entries of this directory. The resulting zipfile "
            "contains the selected format as well as metadata and "
            "images/files if the directory contains any."
        )
    }


@OrgApp.view(model=DirectoryEntryCollection, permission=Private, name='zip')
def view_zip_file(self, request):
    layout = DirectoryEntryCollectionLayout(self, request)

    format = request.params.get('format', 'json')
    formatter = layout.export_formatter(format)

    def transform(key, value):
        return formatter(key), formatter(value)

    with NamedTemporaryFile() as f:
        archive = DirectoryZipArchive(f.name + '.zip', format, transform)
        archive.write(self.directory)

        response = render_file(str(archive.path), request)

    response.headers['Content-Disposition']\
        = 'attachment; filename="{}.zip"'.format(self.directory.name)

    return response


@OrgApp.form(model=DirectoryEntryCollection, permission=Private, name='import',
             template='form.pt', form=DirectoryImportForm)
def view_import(self, request, form):

    layout = DirectoryEntryCollectionLayout(self, request)
    layout.breadcrumbs.append(Link(_("Import"), '#'))
    layout.editbar_links = None

    if form.submitted(request):
        form.run_import(target=self.directory)

        return request.redirect(request.link(self))

    return {
        'layout': layout,
        'title': _("Import"),
        'form': form,
    }
