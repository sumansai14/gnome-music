from gi.repository import Gtk, Gd, GLib, GObject, Grl, Pango
from gi.repository import GdkPixbuf
from gi.repository import Tracker
from gettext import gettext as _
from gnomemusic.grilo import grilo
import logging
from gnomemusic.query import Query
from gnomemusic.albumArtCache import AlbumArtCache

tracker = Tracker.SparqlConnection.get(None)
ALBUM_ART_CACHE = AlbumArtCache.get_default()
NOW_PLAYING_ICON_NAME = 'media-playback-start-symbolic'
ERROR_ICON_NAME = 'dialog-error-symbolic'


class LoadMoreButton:
    def __init__(self, counter):
        self._block = False
        self._counter = counter
        child = Gtk.Grid(column_spacing=10,
                         hexpand=False,
                         halign=Gtk.Align.CENTER,
                         visible=True)
        self._spinner = Gtk.Spinner(halign=Gtk.Align.CENTER,
                                    no_show_all=True)
        self._spinner.set_size_request(16, 16)
        child.add(self._spinner)
        self._label = Gtk.Label(label=_("Load More"),
                                visible=True)
        child.add(self._label)
        self.widget = Gtk.Button(no_show_all=True,
                                 child=child)
        self.widget.get_style_context().add_class('documents-load-more')
        self.widget.connect('clicked', self._on_load_more_clicked)
        self._on_item_count_changed()

    def _on_load_more_clicked(self, data=None):
        self._label.set_label(_("Loading..."))
        self._spinner.show()
        self._spinner.start()

    def _on_item_count_changed(self):
        remaining_docs = self._counter()
        visible = remaining_docs >= 0 and not self._block
        self.widget.set_visible(visible)

        if visible:
            self._label.set_label(_("Load More"))
            self._spinner.stop()
            self._spinner.hide()

    def set_block(self, block):
        if (self._block == block):
            return

        self._block = block
        self._on_item_count_changed()


class AlbumWidget(Gtk.EventBox):

    tracks = []
    duration = 0

    def __init__(self, player):
        super(Gtk.EventBox, self).__init__()
        self.player = player
        self.iterToClean = None
        self.cache = AlbumArtCache.get_default()
        self._symbolicIcon = self.cache.make_default_icon(256, 256)

        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/AlbumWidget.ui')
        self.model = Gtk.ListStore(
            GObject.TYPE_STRING,  # title
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,    # icon
            GObject.TYPE_OBJECT,  # song object
            GObject.TYPE_BOOLEAN,  # item selected
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_BOOLEAN,  # icon shown
        )

        self.view = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )
        self.view.set_view_type(Gd.MainViewType.LIST)
        self.album = None
        self.view.connect('item-activated', self._on_item_activated)

        view_box = self.ui.get_object("view")
        self.ui.get_object("scrolledWindow").set_placement(Gtk.CornerType.
                                                           TOP_LEFT)
        child_view = self.view.get_children()[0]
        child_view.set_margin_top(64)
        child_view.set_margin_bottom(64)
        child_view.set_margin_right(32)
        self.view.remove(child_view)
        view_box.add(child_view)
        self.add(self.ui.get_object("AlbumWidget"))
        self._add_list_renderers()
        # TODO: make this work
        self.get_style_context().add_class("view")
        self.get_style_context().add_class("content-view")
        self.show_all()

    def _on_item_activated(self, widget, id, path):
        _iter = self.model.get_iter(path)
        if(self.model.get_value(_iter, 7) != ERROR_ICON_NAME):
            if (self.iterToClean and self.player.playlistId == self.album):
                item = self.model.get_value(self.iterToClean, 5)
                title = AlbumArtCache.get_media_title(item)
                self.model.set_value(self.iterToClean, 0, title)
                #Hide now playing icon
                self.model.set_value(self.iterToClean, 6, False)
            self.player.set_playlist("Album", self.album, self.model, _iter, 5)
            self.player.set_playing(True)

    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()

        cols = list_widget.get_columns()
        cols[0].set_min_width(310)
        cols[0].set_max_width(470)
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        cells[1].set_visible(False)

        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xpad=0,
                                                             xalign=1.0,
                                                             yalign=0.5)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_fixed_width(24)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         "visible", 9)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         "icon_name", 7)
        list_widget.insert_column(column_now_playing, 0)

        type_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0
        )
        list_widget.add_renderer(type_renderer, lambda *args: None, None)
        cols[0].clear_attributes(type_renderer)
        cols[0].add_attribute(type_renderer, "markup", 0)

        durationRenderer = Gd.StyledTextRenderer(
            xpad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=1.0
        )
        durationRenderer.add_class('dim-label')
        list_widget.add_renderer(durationRenderer, lambda *args: None, None)
        cols[0].clear_attributes(durationRenderer)
        cols[0].add_attribute(durationRenderer, "markup", 1)

    def update(self, artist, album, item, header_bar, selection_toolbar):
        self.selection_toolbar = selection_toolbar
        self.header_bar = header_bar
        self.album = album
        self.ui.get_object("cover").set_from_pixbuf(self._symbolicIcon)
        ALBUM_ART_CACHE.lookup(256, artist,
                               item.get_string(Grl.METADATA_KEY_ALBUM),
                               self._on_look_up)

        # if the active queue has been set by self album,
        # use it as model, otherwise build the liststore
        cached_playlist = self.player.running_playlist("Album", album)
        if cached_playlist:
            self.model = cached_playlist
            self.update_model(self.player, cached_playlist,
                              self.player.currentTrack)
        else:
            self.model = Gtk.ListStore(GObject.TYPE_STRING,  # title
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_STRING,
                                       GdkPixbuf.Pixbuf,    # icon
                                       GObject.TYPE_OBJECT,  # song object
                                       GObject.TYPE_BOOLEAN,  # icon shown
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_BOOLEAN,
                                       GObject.TYPE_BOOLEAN,
                                       )
            GLib.idle_add(grilo.populate_album_songs, item.get_id(),
                          self._on_populate_album_songs)
        header_bar._selectButton.connect('toggled',
                                         self._on_header_select_button_toggled)
        header_bar._cancelButton.connect('clicked',
                                         self._on_header_cancel_button_clicked)
        self.view.connect('view-selection-changed',
                          self._on_view_selection_changed)
        self.view.set_model(self.model)
        escapedArtist = GLib.markup_escape_text(artist)
        escapedAlbum = GLib.markup_escape_text(album)
        self.ui.get_object("artist_label").set_markup(escapedArtist)
        self.ui.get_object("title_label").set_markup(escapedAlbum)
        if (item.get_creation_date()):
            self.ui.get_object("released_label_info").set_text(
                str(item.get_creation_date().get_year()))
        else:
            self.ui.get_object("released_label_info").set_text("----")
        self.player.connect('playlist-item-changed', self.update_model)
        #self.emit('loaded')

    def _on_view_selection_changed(self, widget):
        items = self.view.get_selection()
        self.selection_toolbar\
            ._add_to_playlist_button.set_sensitive(len(items) > 0)

    def _on_header_cancel_button_clicked(self, button):
        self.view.set_selection_mode(False)
        self.header_bar.set_selection_mode(False)
        self.header_bar.header_bar.title = self.album

    def _on_header_select_button_toggled(self, button):
        if button.get_active():
            self.view.set_selection_mode(True)
            self.header_bar.set_selection_mode(True)
            self.player.eventBox.set_visible(False)
            self.selection_toolbar.eventbox.set_visible(True)
            self.selection_toolbar._add_to_playlist_button.sensitive = False
        else:
            self.view.set_selection_mode(False)
            self.header_bar.set_selection_mode(False)
            self.header_bar.title = self.album
            self.selection_toolbar.eventbox.set_visible(False)
            if(self.player.get_playback_status() != 'Stopped'):
                self.player.eventBox.set_visible(True)

    def _on_populate_album_songs(self, source, prefs, track):
        if track:
            self.tracks.append(track)
            self.duration = self.duration + track.get_duration()
            _iter = self.model.append()
            escapedTitle = AlbumArtCache.get_media_title(track, True)
            try:
                self.player.discoverer.discover_uri(track.get_url())
                self.model.set(_iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle,
                                self.player.seconds_to_string(
                                    track.get_duration()),
                                "", "", None, track, NOW_PLAYING_ICON_NAME,
                                False])
            except Exception as err:
                logging.debug(err.message)
                logging.debug("failed to discover url " + track.get_url())
                self.model.set(_iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle, "", "", "", None,
                                track, ERROR_ICON_NAME, True])
            self.ui.get_object("running_length_label_info").set_text(
                "%d min" % (int(self.duration / 60) + 1))

    def _on_look_up(self, pixbuf, path):
        _iter = self.iterToClean
        if pixbuf:
            self.ui.get_object("cover").set_from_pixbuf(pixbuf)
            self.model.set(_iter, [4], [pixbuf])

    def update_model(self, player, playlist, currentIter):
        #self is not our playlist, return
        if (playlist != self.model):
            return False
        currentSong = playlist.get_value(currentIter, 5)
        song_passed = False
        _iter = playlist.get_iter_first()
        while _iter:
            song = playlist.get_value(_iter, 5)

            escapedTitle = AlbumArtCache.get_media_title(song, True)
            if (song == currentSong):
                title = "<b>%s</b>" % escapedTitle
                iconVisible = True
                song_passed = True
            elif (song_passed):
                title = "<span>%s</span>" % escapedTitle
                iconVisible = False
            else:
                title = "<span color='grey'>%s</span>" % escapedTitle
                iconVisible = False
            playlist.set_value(_iter, 0, title)
            if(playlist.get_value(_iter, 7) != ERROR_ICON_NAME):
                playlist.set_value(_iter, 9, iconVisible)
            _iter = playlist.iter_next(_iter)
        return False


class ArtistAlbums(Gtk.VBox):
    def __init__(self, artist, albums, player):
        Gtk.VBox.__init__(self)
        self.player = player
        self.artist = artist
        self.albums = albums
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumsWidget.ui')
        self.set_border_width(0)
        self.ui.get_object("artist").set_label(self.artist)
        self.widgets = []

        self.model = Gtk.ListStore(GObject.TYPE_STRING,   # title
                                   GObject.TYPE_STRING,
                                   GObject.TYPE_STRING,
                                   GObject.TYPE_BOOLEAN,  # icon shown
                                   GObject.TYPE_STRING,   # icon
                                   GObject.TYPE_OBJECT,   # song object
                                   GObject.TYPE_BOOLEAN
                                   )

        self._hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._albumBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 spacing=48)
        self._scrolledWindow = Gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC)
        self._scrolledWindow.add(self._hbox)
        self._hbox.pack_start(self.ui.get_object('ArtistAlbumsWidget'),
                              False, False, 0)
        self._hbox.pack_start(self._albumBox, False, False, 16)
        self.pack_start(self._scrolledWindow, True, True, 0)

        for album in albums:
            self.add_album(album)

        self.show_all()
        self.player.connect('playlist-item-changed', self.update_model)

    def add_album(self, album):
        widget = ArtistAlbumWidget(self.artist, album, self.player, self.model)
        self._albumBox.pack_start(widget, False, False, 0)
        self.widgets.append(widget)

    def update_model(self, player, playlist, currentIter):
        #this is not our playlist, return
        if playlist != self.model:
            #TODO, only clean once, but that can wait util we have clean
            #the code a bit, and until the playlist refactoring.
            #the overhead is acceptable for now
            self.clean_model()
            return False

        currentSong = playlist.get_value(currentIter, 5)
        song_passed = False
        itr = playlist.get_iter_first()

        while itr:
            song = playlist.get_value(itr, 5)
            song_widget = song.song_widget

            if not song_widget.can_be_played:
                itr = playlist.iter_next(itr)
                continue

            escapedTitle = AlbumArtCache.get_media_title(song, True)
            if (song == currentSong):
                song_widget.now_playing_sign.show()
                song_widget.title.set_markup("<b>%s</b>" % escapedTitle)
                song_passed = True
            elif (song_passed):
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup("<span>%s</span>" % escapedTitle)
            else:
                song_widget.now_playing_sign.hide()
                song_widget.title\
                    .set_markup("<span color='grey'>%s</span>" % escapedTitle)
            itr = playlist.iter_next(itr)
        return False

    def clean_model(self):
        itr = self.model.get_iter_first()
        while itr:
            song = self.model.get_value(itr, 5)
            song_widget = song.song_widget
            escapedTitle = AlbumArtCache.get_media_title(song, True)
            if song_widget.can_be_played:
                song_widget.now_playing_sign.hide()
            song_widget.title.set_markup("<span>%s</span>" % escapedTitle)
            itr = self.model.iter_next(itr)
        return False


class AllArtistsAlbums(ArtistAlbums):

    def __init__(self, player):
        ArtistAlbums.__init__(self, _("All Artists"), [], player)
        self._offset = 0
        self.countQuery = Query.ALBUMS_COUNT
        self._load_more = LoadMoreButton(self._get_remaining_item_count)
        self.pack_end(self._load_more.widget, False, False, 0)
        self._load_more.widget.connect("clicked", self._populate)
        self._connect_view()
        self._populate()

    def _connect_view(self):
        self._adjustmentValueId =\
            self._scrolledWindow.get_vadjustment()\
                .connect('value-changed', self._on_scrollbar_visible)
        self._adjustmentChangedId =\
            self._scrolledWindow.get_vadjustment().connect(
                'changed', self._on_scrollbar_visible)
        self._scrollbarVisibleId =\
            self._scrolledWindow.get_vscrollbar().connect(
                'notify::visible',
                self._on_scrollbar_visible)
        self._on_scrollbar_visible()

    def _on_scrollbar_visible(self, scrollbar=None, pspec=None, data=None):
        self._on_scrolled_win_change()

    def _on_scrolled_win_change(self, scrollbar=None, pspec=None, data=None):
        vScrollbar = self._scrolledWindow.get_vscrollbar()
        adjustment = self._scrolledWindow.get_vadjustment()
        revealAreaHeight = 32

        # if there's no vscrollbar, or if it's not visible, hide the button
        if not vScrollbar or not vScrollbar.get_visible():
            self._load_more.set_block(True)
            return

        value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()
        end = False

        # special case self values which happen at construction
        if (((value != 0) or (upper != 1) or (page_size != 1))
                and self._get_remaining_item_count() > 0):
            end = not (value < (upper - page_size - revealAreaHeight))
        self._load_more.set_block(not end)

    def _populate(self, data=None):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_albums,
                          self._offset, self.add_item, 5)

    def add_item(self, source, param, item):
        if item:
            self._offset += 1
            self.add_album(item)

    def _get_remaining_item_count(self):
        count = -1
        if self.countQuery:
            cursor = tracker.query(self.countQuery, None)
            if cursor and cursor.next(None):
                count = cursor.get_integer(0)
        return count - self._offset


class ArtistAlbumWidget(Gtk.HBox):

    def __init__(self, artist, album, player, model):
        super(Gtk.HBox, self).__init__()
        self.player = player
        self.album = album
        self.artist = artist
        self.model = model
        self.songs = []

        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumWidget.ui')

        self.cache = AlbumArtCache.get_default()
        pixbuf = self.cache.make_default_icon(128, 128)
        GLib.idle_add(self._update_album_art)

        self.ui.get_object("cover").set_from_pixbuf(pixbuf)
        self.ui.get_object("title").set_label(album.get_title())
        if album.get_creation_date():
            self.ui.get_object("year").set_markup(
                "<span color='grey'>(%s)</span>" %
                str(album.get_creation_date().get_year())
            )
        self.tracks = []
        GLib.idle_add(grilo.populate_album_songs,
                      album.get_id(), self.get_songs)
        self.pack_start(self.ui.get_object("ArtistAlbumWidget"), True, True, 0)
        self.show_all()

    def get_songs(self, source, prefs, track):
        if track:
            self.tracks.append(track)
        else:
            for i, track in enumerate(self.tracks):
                ui = Gtk.Builder()
                ui.add_from_resource('/org/gnome/Music/TrackWidget.ui')
                song_widget = ui.get_object("eventbox1")
                self.songs.append(song_widget)
                ui.get_object("num")\
                    .set_markup("<span color='grey'>%d</span>"
                                % len(self.songs))
                title = AlbumArtCache.get_media_title(track)
                ui.get_object("title").set_text(title)
                ui.get_object("title").set_alignment(0.0, 0.5)
                self.ui.get_object("grid1").attach(
                    song_widget,
                    int(i / (len(self.tracks) / 2)),
                    int(i % (len(self.tracks) / 2)), 1, 1
                )
                track.song_widget = song_widget
                itr = self.model.append()
                song_widget._iter = itr
                song_widget.model = self.model
                song_widget.title = ui.get_object("title")

                try:
                    self.player.discoverer.discover_uri(track.get_url())
                    self.model.set(itr,
                                   [0, 1, 2, 3, 4, 5],
                                   [title, "", "", False,
                                    NOW_PLAYING_ICON_NAME, track])
                    song_widget.now_playing_sign = ui.get_object("image1")
                    song_widget.now_playing_sign.set_from_icon_name(
                        NOW_PLAYING_ICON_NAME,
                        Gtk.IconSize.SMALL_TOOLBAR)
                    song_widget.now_playing_sign.set_no_show_all("True")
                    song_widget.now_playing_sign.set_alignment(0.0, 0.6)
                    song_widget.can_be_played = True
                    song_widget.connect('button-release-event',
                                        self.track_selected)

                except:
                    print("failed to discover url " + track.get_url())
                    self.model.set(itr, [0, 1, 2, 3, 4, 5],
                                   [title, "", "", True,
                                    ERROR_ICON_NAME, track])
                    song_widget.now_playing_sign = ui.get_object("image1")
                    song_widget.now_playing_sign.set_from_icon_name(
                        ERROR_ICON_NAME,
                        Gtk.IconSize.SMALL_TOOLBAR)
                    song_widget.now_playing_sign.set_alignment(0.0, 0.6)
                    song_widget.can_be_played = False
            self.ui.get_object("grid1").show_all()

    def _update_album_art(self):
        ALBUM_ART_CACHE.lookup(128, self.artist,
                               self.album.get_title(), self.get_album_cover)

    def get_album_cover(self, pixbuf, path):
        if pixbuf:
            self.ui.get_object("cover").set_from_pixbuf(pixbuf)
        else:
            options = Grl.OperationOptions()
            options.set_flags(Grl.ResolutionFlags.FULL
                              | Grl.ResolutionFlags.IDLE_RELAY)
            grilo.tracker.resolve(self.album,
                                  [Grl.METADATA_KEY_THUMBNAIL],
                                  options, self.load_cover, None)

    def load_cover(self, source, param, item, data, error):
        uri = self.album.get_thumbnail()
        ALBUM_ART_CACHE.get_from_uri(uri, self.artist,
                                     self.album.get_title(), 128, 128,
                                     self.get_album_cover)

    def track_selected(self, widget, _iter):
        self.player.stop()
        self.player.set_playlist("Artist", self.album,
                                 widget.model, widget._iter, 5)
        self.player.set_playing(True)
