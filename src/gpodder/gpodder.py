# -*- coding: UTF8 -*-

# Python module src/gpodder/gpodder.py
# Autogenerated from gpodder.glade
# Generated on Fri Apr  7 20:11:08 2006

# Warning: Do not modify any context comment such as #--
# They are required to keep user's code

#
# gPodder
# Copyright (c) 2005 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
#

import os
import gtk
import gobject
import sys

from threading import Event
from threading import Thread
from string import strip


from SimpleGladeApp import SimpleGladeApp
from SimpleGladeApp import bindtextdomain

from libpodcasts import podcastChannel
from libpodcasts import podcastItem

from libpodcasts import channelsToModel

from librssreader import rssReader
from libopmlwriter import opmlWriter
from libwget import downloadThread
from libwget import downloadStatusManager

from libgpodder import gPodderLib
from libgpodder import gPodderChannelReader
from libgpodder import gPodderChannelWriter

from liblocaldb import localDB

from libplayers import UserAppsReader

from libipodsync import gPodder_iPodSync
from libipodsync import ipod_supported

# for isDebugging:
import libgpodder

app_name = "gpodder"
app_version = "unknown" # will be set in main() call
app_authors = [
                'Thomas Perl <thp@perli.net>', '',
                _('Contributors / patch writers:'),
                'Peter Hoffmann <tosh@cs.tu-berlin.de>',
                'Adrien Beaucreux <informancer@web.de>',
                'Alain Tauch <contrib@maisondubonheur.com>', '',
                _('See the AUTHORS file for all contributors')
              ]
app_copyright = 'Copyright (c) 2005-2006 Thomas Perl'
app_website = 'http://perli.net/projekte/gpodder/'

glade_dir = '/usr/share/gpodder/'
icon_dir = '/usr/share/gpodder/images/gpodder.png'
artwork_dir = '/usr/share/gpodder/images/'
locale_dir = '/usr/share/locale/'

class Gpodder(SimpleGladeApp):
    channels = []
    
    active_item = None
    items_model = None
    
    active_channel = None
    channels_model = None

    channels_loaded = False

    download_status_manager = None
    tooltips = None

    # Local DB
    ldb = None

    # User Apps Reader
    uar = None

    def __init__(self, path="gpodder.glade",
                 root="gPodder",
                 domain=app_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    #-- Gpodder.new {
    def new(self):
        if libgpodder.isDebugging():
            print "A new %s has been created" % self.__class__.__name__

        #self.gPodder.set_title( self.gPodder.get_title())
        #self.statusLabel.set_text( "Welcome to gPodder! Suggestions? Mail to: thp@perli.net")
        # set up the rendering of the comboAvailable combobox
        cellrenderer = gtk.CellRendererText()
        self.comboAvailable.pack_start( cellrenderer, True)
        self.comboAvailable.add_attribute( cellrenderer, 'text', 1)

        # set up the rendering of the comboDownloaded combobox
        cellrenderer = gtk.CellRendererText()
        self.comboDownloaded.pack_start( cellrenderer, True)
        self.comboDownloaded.add_attribute( cellrenderer, 'text', 1)

        #See http://www.pygtk.org/pygtk2tutorial/sec-CellRenderers.html
        #gtk.TreeViewColumn( "", gtk.CellRendererToggle(), active=3),
        namecell = gtk.CellRendererText()
        namecell.set_property('cell-background', 'white')
        namecolumn = gtk.TreeViewColumn( _("Episode"), namecell, text=1)
        namecolumn.add_attribute(namecell, "cell-background", 4)        

        sizecell = gtk.CellRendererText()
        sizecell.set_property('cell-background', 'white')
        sizecolumn = gtk.TreeViewColumn( _("Size"), sizecell, text=2)
        sizecolumn.add_attribute(sizecell, "cell-background", 4)
        
        for itemcolumn in ( namecolumn, sizecolumn ):
            self.treeAvailable.append_column( itemcolumn)
        
        # columns and renderers for the "downloaded" tab
        # more information: see above..
        namecell = gtk.CellRendererText()
        namecell.set_property('cell-background', 'white')
        namecolumn = gtk.TreeViewColumn( _("Episode"), namecell, text=1)
        namecolumn.add_attribute(namecell, "cell-background", 4)
        self.treeDownloaded.append_column( namecolumn)
        
        # columns and renderers for "download progress" tab
        episodecell = gtk.CellRendererText()
        episodecolumn = gtk.TreeViewColumn( _("Episode"), episodecell, text=0)
        
        speedcell = gtk.CellRendererText()
        speedcolumn = gtk.TreeViewColumn( _("Speed"), speedcell, text=1)
        
        progresscell = gtk.CellRendererProgress()
        progresscolumn = gtk.TreeViewColumn( _("Progress"), progresscell, value=2)
        
        for itemcolumn in ( episodecolumn, speedcolumn, progresscolumn ):
            self.treeDownloads.append_column( itemcolumn)
    
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.download_status_manager = downloadStatusManager()
        self.treeDownloads.set_model( self.download_status_manager.getModel())
        
        # read and display subscribed channels
        reader = gPodderChannelReader()
        self.channels = reader.read( False)
        self.channels_loaded = True

        # keep Downloaded channels list
        self.downloaded_channels = None
        self.active_downloaded_channels = 0
        
        # update view
        self.updateComboBox()
        self.updateDownloadedComboBox()

        # tooltips :)
        self.tooltips = gtk.Tooltips()
        self.tooltips.set_tip( self.btnEditChannel, _("Channel Info"))
        
        #Add Drag and Drop Support
        targets = [("text/plain", 0, 2), ('STRING', 0, 3), ('TEXT', 0, 4)]
        self.main_widget.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets, \
                        gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY | \
                        gtk.gdk.ACTION_DEFAULT)
        self.main_widget.connect("drag_data_received", self.drag_data_received)
        self.wNotebook.connect("switch-page", self.switched_notebook)

        # disable iPod sync features if not supported
        if not ipod_supported():
            self.cleanup_ipod.set_sensitive( False)
            self.sync_to_ipod.set_sensitive( False)

        # if we are running a SVN-based version, notify the user :)
        if app_version.rfind( "svn") != -1:
            self.showMessage( _("<b>gPodder development version %s</b>\nUse at your own risk, but also enjoy new features :)") % app_version)
    #-- Gpodder.new }

    #-- Gpodder custom methods {
    #   Write your own methods here
    def updateComboBox( self):
        self.channels_model = channelsToModel( self.channels)
        
        self.comboAvailable.set_model( self.channels_model)
        try:
            self.comboAvailable.set_active( 0)
        except:
            pass
        #self.updateTreeView()

    def updateDownloadedComboBox( self):
        # now, update downloaded feeds tab:
        if self.ldb == None:
            self.ldb = localDB()
        # update downloaded_channels list
        self.downloaded_channels = self.ldb.getDownloadedChannelsList()
        self.comboDownloaded.set_model( self.ldb.getDownloadedChannelsModel())
        try:
            self.comboDownloaded.set_active( self.active_downloaded_channels)
        except:
            self.active_downloaded_channels = 0
            if libgpodder.isDebugging():
              print _('No downloaded podcasts found.')
    # end of self.updateDownloadedComboBox()
    
    def updateTreeView( self):
        try:
            self.items_model = self.channels[self.active_channel].getItemsModel()
            self.treeAvailable.set_model( self.items_model)
        except:
            if self.items_model != None:
                self.items_model.clear()
            self.showMessage( _("<b>No channels found</b>\n\nClick on <b><i>Channels</i></b> &gt; <b><i>Add channel..</i></b> to add a new channel."))
    
    def showMessage( self, message, title = _('gPodder message')):
        dlg = gtk.MessageDialog( self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
        dlg.set_title( title)
        dlg.set_markup( message)
        
        dlg.run()
        dlg.destroy()

    def showConfirmation( self, message = _('Do you really want to do this?'), title = _('gPodder confirmation')):
        myresult = False
        dlg = gtk.MessageDialog( self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
        dlg.set_title( title)
        dlg.set_markup( message)

        if gtk.RESPONSE_YES == dlg.run():
            myresult = True
        
        dlg.destroy()
        if libgpodder.isDebugging():
            print "I Asked: %s" % message
            print "User answered: %s" % str(myresult)
        return myresult

    def set_icon(self):
        icon = self.get_icon('gpodder')
        self.main_widget.set_icon(icon)

    def get_icon(self, entry, size=24):
        #path = self.custom_handler.getIconPath(entry, size)
        path = icon_dir
        if path == None:
            pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size, size)
            pb.fill(0x00000000)
        else:
            try:
                pb = gtk.gdk.pixbuf_new_from_file_at_size(path, size, size)
            except:
                pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, size, size)
                pb.fill(0x00000000)
        return pb

    def switched_notebook( self, notebook, page, page_num):
        # if we are NOT on the "available downloads" page, disable menu items
        if page_num != 0:
            is_available = False
        else:
            is_available = True
        
        # disable/enable menu items related to only the first notebook tab
        self.itemRemoveChannel.set_sensitive( is_available)
        self.itemEditChannel.set_sensitive( is_available)

        # when switching to last page, update the "downloaded" combo box
        if page_num == 2:
            self.updateDownloadedComboBox()

    def drag_data_received(self, widget, context, x, y, sel, ttype, time):
        result = sel.data
        self.add_new_channel( result)

    def refetch_channel_list( self):
        channels_should_be = len( self.channels)
        
        # fetch metadata for that channel
        gPodderChannelWriter().write( self.channels)
        self.channels = gPodderChannelReader().read( False)
        
        # fetch feed for that channel
        gPodderChannelWriter().write( self.channels)
        self.channels = gPodderChannelReader().read( False)
        
        # check if gPodderChannelReader has successfully added the channel
        if channels_should_be > len( self.channels):
            self.showMessage( _("There has been an error adding the channel.\nMaybe the URL is wrong?"))
    
    def add_new_channel( self, result = None):
        if result != None and result != "" and (result[:4] == "http" or result[:3] == "ftp"):
            if libgpodder.isDebugging():
                print ("Will add channel :%s") % result
            self.statusLabel.set_text( _("Fetching channel index..."))
            channel_new = podcastChannel( result)
            channel_new.shortname = "__unknown__"
            self.channels.append( channel_new)
            
            # download changed channels
            self.refetch_channel_list()

            # try to update combo box
            self.updateComboBox()
            self.statusLabel.set_text( "")
        else:
            if result != None and result != "":
                self.showMessage( _("Could not add new channel.\nOnly <b>http://</b> and <b>ftp://</b> URLs supported at the moment."))
    
    def get_current_channel_downloaded( self):
        iter = self.comboDownloaded.get_active_iter()
        return self.comboDownloaded.get_model().get_value( iter, 0)
    
    def sync_to_ipod_proc( self, sync_win):
        gpl = gPodderLib()
        gpl.loadConfig()
        sync = gPodder_iPodSync( ipod_mount = gpl.ipod_mount, callback_status = sync_win.set_status, callback_progress = sync_win.set_progress, callback_done = sync_win.close)
        if not sync.open():
            gobject.idle_add( self.showMessage, _('Cannot access iPod at %s.\nMake sure your iPod is connected and mounted.') % gpl.ipod_mount)
            sync.close()
            return False
        for channel in self.downloaded_channels:
            channel.set_metadata_from_localdb()
            sync.copy_channel_to_ipod( channel)
        sync.close()

    def ipod_cleanup_proc( self, sync_win):
        gpl = gPodderLib()
        gpl.loadConfig()
        sync = gPodder_iPodSync( ipod_mount = gpl.ipod_mount, callback_status = sync_win.set_status, callback_progress = sync_win.set_progress, callback_done = sync_win.close)
        if not sync.open():
            gobject.idle_add( self.showMessage, _('Cannot access iPod at %s.\nMake sure your iPod is connected and mounted.') % gpl.ipod_mount)
            sync.close()
            return False
        sync.clean_playlist()
        sync.close()
    #-- Gpodder custom methods }

    #-- Gpodder.close_gpodder {
    def close_gpodder(self, widget, *args):
        if libgpodder.isDebugging():
            print "close_gpodder called with self.%s" % widget.get_name()
        
        if self.channels_loaded:
            gPodderChannelWriter().write( self.channels)

        # cancel downloads by killing all threads in the list
        if self.download_status_manager:
            self.download_status_manager.cancelAll()

        self.gtk_main_quit()
    #-- Gpodder.close_gpodder }

    #-- Gpodder.on_itemUpdate_activate {
    def on_itemUpdate_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemUpdate_activate called with self.%s" % widget.get_name()
        reader = gPodderChannelReader()
        #self.channels = reader.read( True)
        #self.labelStatus.set_text( "Updating feed cache...")
        please_wait = gtk.MessageDialog()
        please_wait.set_markup( _("<big><b>Updating feed cache</b></big>\n\nPlease wait while gPodder is\nupdating the feed cache..."))
        please_wait.show()
        self.channels = reader.read( True)
        please_wait.destroy()
        #self.labelStatus.set_text( "")
        self.updateComboBox()
    #-- Gpodder.on_itemUpdate_activate }

    #-- Gpodder.on_sync_to_ipod_activate {
    def on_sync_to_ipod_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_sync_to_ipod_activate called with self.%s" % widget.get_name()
        sync_win = Gpoddersync()
        while gtk.events_pending():
            gtk.main_iteration( False)
        args = ( sync_win, )
        thread = Thread( target = self.sync_to_ipod_proc, args = args)
        thread.start()
    #-- Gpodder.on_sync_to_ipod_activate }

    #-- Gpodder.on_cleanup_ipod_activate {
    def on_cleanup_ipod_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_cleanup_ipod_activate called with self.%s" % widget.get_name()
        sync_win = Gpoddersync()
        while gtk.events_pending():
            gtk.main_iteration( False)
        args = ( sync_win, )
        thread = Thread( target = self.ipod_cleanup_proc, args = args)
        thread.start()
    #-- Gpodder.on_cleanup_ipod_activate }

    #-- Gpodder.on_itemPreferences_activate {
    def on_itemPreferences_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemPreferences_activate called with self.%s" % widget.get_name()
        if self.uar == None:
            self.uar = UserAppsReader()
            self.uar.read()
        prop = Gpodderproperties()
        prop.set_uar( self.uar)
    #-- Gpodder.on_itemPreferences_activate }

    #-- Gpodder.on_itemAddChannel_activate {
    def on_itemAddChannel_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemAddChannel_activate called with self.%s" % widget.get_name()
        ch = Gpodderchannel()
        ch.entryURL.set_text( "http://")
        result = ch.requestURL()
        self.add_new_channel( result)
    #-- Gpodder.on_itemAddChannel_activate }

    #-- Gpodder.on_itemEditChannel_activate {
    def on_itemEditChannel_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemEditChannel_activate called with self.%s" % widget.get_name()
        channel = None
        try:
            channel = self.channels[self.active_channel]
        except:
            self.showMessage( _("Cannot edit this channel.\n\nNo channel found."))
            return
        
        result = Gpodderchannel().requestURL( channel)
        if result != channel.url and result != None and result != "" and (result[:4] == "http" or result[:3] == "ftp"):
            if libgpodder.isDebugging():
                print 'Changing ID %d from "%s" to "%s"' % (active, channel.url, result)
            self.statusLabel.set_text( _("Fetching channel index..."))
            channel_new = podcastChannel( result)
            channel_new.shortname = "__unknown__"
            new_channels = self.channels[0:active]
            new_channels.append( channel_new)
            new_channels.extend( self.channels[active+1:])
            self.channels = new_channels
            
            # fetch new channels
            self.refetch_channel_list()
            
            self.updateComboBox()
            self.statusLabel.set_text( "")
        # end if result != None etc etc
    #-- Gpodder.on_itemEditChannel_activate }

    #-- Gpodder.on_itemRemoveChannel_activate {
    def on_itemRemoveChannel_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemRemoveChannel_activate called with self.%s" % widget.get_name()
        
        try:
            if self.showConfirmation( _("Do you really want to remove this channel?\n\n %s") % self.channels[self.active_channel].title) == False:
                return
            self.channels.remove( self.channels[self.active_channel])
            gPodderChannelWriter().write( self.channels)
            self.channels = gPodderChannelReader().read( False)
            self.updateComboBox()
        except:
            self.showMessage( _("Could not delete channel.\nProbably no channel is selected."))
    #-- Gpodder.on_itemRemoveChannel_activate }

    #-- Gpodder.on_itemExportChannels_activate {
    def on_itemExportChannels_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemExportChannels_activate called with self.%s" % widget.get_name()
        if len( self.channels) == 0:
          self.showMessage( _("Your channel list is empty. Nothing to export."))
          return
        dlg = gtk.FileChooserDialog( title=_("Export to OPML"), parent = None, action = gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button( gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            foutname = dlg.get_filename()
            if foutname[-5:] != ".opml" and foutname[-4:] != ".xml":
                foutname = foutname + ".opml"
            if libgpodder.isDebugging():
                print 'Exporting channels list to: %s' % foutname
            w = opmlWriter( foutname)
            for ch in self.channels:
                w.addChannel( ch)
            w.close()
        # end response is ok
        dlg.destroy()
    # end dlg.run()
    #-- Gpodder.on_itemExportChannels_activate }

    #-- Gpodder.on_itemAbout_activate {
    def on_itemAbout_activate(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_itemAbout_activate called with self.%s" % widget.get_name()
        dlg = gtk.AboutDialog()
        dlg.set_name( app_name)
        dlg.set_version( app_version)
        dlg.set_authors( app_authors)
        dlg.set_copyright( app_copyright)
        dlg.set_website( app_website)
        dlg.set_translator_credits( _('translator-credits'))
        #
        try:
            dlg.set_logo( gtk.gdk.pixbuf_new_from_file_at_size( icon_dir, 164, 164))
        except:
            None
        #
        dlg.run()
    #-- Gpodder.on_itemAbout_activate }

    #-- Gpodder.on_wNotebook_switch_page {
    def on_wNotebook_switch_page(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_wNotebook_switch_page called with self.%s" % widget.get_name()
    #-- Gpodder.on_wNotebook_switch_page }

    #-- Gpodder.on_comboAvailable_changed {
    def on_comboAvailable_changed(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_comboAvailable_changed called with self.%s" % widget.get_name()
        self.active_channel = self.comboAvailable.get_active()
        self.updateTreeView()
    #-- Gpodder.on_comboAvailable_changed }

    #-- Gpodder.on_btnEditChannel_clicked {
    def on_btnEditChannel_clicked(self, widget, *args):
        if libgpodder.isDebugging():
           print "on_btnEditChannel_clicked called with self.%s" % widget.get_name()
        self.on_itemEditChannel_activate( widget, args)
    #-- Gpodder.on_btnEditChannel_clicked }

    #-- Gpodder.on_treeAvailable_row_activated {
    def on_treeAvailable_row_activated(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_treeAvailable_row_activated called with self.%s" % widget.get_name()
        try:
            selection_tuple = self.treeAvailable.get_selection().get_selected()
            selection_iter = selection_tuple[1]
            url = self.items_model.get_value( selection_iter, 0)
        except:
            self.showMessage( _("You have not selected an episode to download."))
            return

        self.active_item = self.channels[self.active_channel].getActiveByUrl( url)
        
        current_channel = self.channels[self.active_channel]
        current_podcast = current_channel.items[self.active_item]
        filename = current_channel.getPodcastFilename( current_podcast.url)
        if widget.get_name() == "treeAvailable":
            Gpodderepisode().set_episode( current_podcast)
            return
        
        if os.path.exists( filename) == False and self.download_status_manager.is_download_in_progress( current_podcast.url) == False:
            downloadThread( current_podcast.url, filename, None, self.download_status_manager, current_podcast.title, current_channel, current_podcast, self.ldb).download()
        else:
            self.showMessage( _("You have already downloaded this episode\nor you are currently downloading it."))
            # if we're not downloading it, but it exists: add to localdb (if not already done so)
            if os.path.exists( filename) == True:
                if libgpodder.isDebugging():
                    print "already downloaded, trying to add to localDB if needed"
                if current_channel.addDownloadedItem( current_podcast):
                    self.ldb.clear_cache()
    #-- Gpodder.on_treeAvailable_row_activated }

    #-- Gpodder.on_btnDownload_clicked {
    def on_btnDownload_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnDownload_clicked called with self.%s" % widget.get_name()
        self.on_treeAvailable_row_activated( widget, args)
    #-- Gpodder.on_btnDownload_clicked }

    #-- Gpodder.on_treeDownloads_row_activated {
    def on_treeDownloads_row_activated(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_treeDownloads_row_activated called with self.%s" % widget.get_name()
        selection_tuple = self.treeDownloads.get_selection().get_selected()
        selection_iter = selection_tuple[1]
        if selection_iter != None:
            url = self.download_status_manager.get_url_by_iter( selection_iter)
            title = self.download_status_manager.get_title_by_iter( selection_iter)
            if self.showConfirmation( _("Do you really want to cancel this download?\n\n%s") % title):
                self.download_status_manager.cancel_by_url( url)
        else:
            self.showMessage( _("No episode selected."))
    #-- Gpodder.on_treeDownloads_row_activated }

    #-- Gpodder.on_btnCancelDownloadStatus_clicked {
    def on_btnCancelDownloadStatus_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnCancelDownloadStatus_clicked called with self.%s" % widget.get_name()
        self.on_treeDownloads_row_activated( widget, None)
    #-- Gpodder.on_btnCancelDownloadStatus_clicked }

    #-- Gpodder.on_comboDownloaded_changed {
    def on_comboDownloaded_changed(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_comboDownloaded_changed called with self.%s" % widget.get_name()
        self.active_downloaded_channels = self.comboDownloaded.get_active()
        try:
          filename = self.get_current_channel_downloaded()
          new_model = self.ldb.getDownloadedEpisodesModelByFilename( filename)
          self.treeDownloaded.set_model( new_model)
        except:
          # silently ignore the fact that we do not have any downloads
          pass
    #-- Gpodder.on_comboDownloaded_changed }

    #-- Gpodder.on_treeDownloaded_row_activated {
    def on_treeDownloaded_row_activated(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_treeDownloaded_row_activated called with self.%s" % widget.get_name()
        try:
          channel_filename = self.get_current_channel_downloaded()
          
          selection_tuple = self.treeDownloaded.get_selection().get_selected()
          selection_iter = selection_tuple[1]
          url = self.treeDownloaded.get_model().get_value( selection_iter, 0)
          filename_final = self.ldb.getLocalFilenameByPodcastURL( channel_filename, url)
          gPodderLib().openFilename( filename_final)
        except:
          self.showMessage( _("No episode selected."))
    #-- Gpodder.on_treeDownloaded_row_activated }

    #-- Gpodder.on_btnDownloadedExecute_clicked {
    def on_btnDownloadedExecute_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnDownloadedExecute_clicked called with self.%s" % widget.get_name()
        self.on_treeDownloaded_row_activated( widget, args)
    #-- Gpodder.on_btnDownloadedExecute_clicked }

    #-- Gpodder.on_btnDownloadedDelete_clicked {
    def on_btnDownloadedDelete_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnDownloadedDelete_clicked called with self.%s" % widget.get_name()
        
        # Note: same code as in on_treeDownloaded_row_activated() TODO: refactor!
        try:
            channel_filename = self.get_current_channel_downloaded()
            
            selection_tuple = self.treeDownloaded.get_selection().get_selected()
            selection_iter = selection_tuple[1]
            
            url = self.treeDownloaded.get_model().get_value( selection_iter, 0)
            title = self.treeDownloaded.get_model().get_value( selection_iter, 1)
            filename_final = self.ldb.getLocalFilenameByPodcastURL( channel_filename, url)
            current_channel = self.downloaded_channels[self.comboDownloaded.get_active()]
            if self.showConfirmation( _("Do you really want to remove this episode?\n\n%s") % title) == False:
                return
            
            if current_channel.deleteDownloadedItemByUrlAndTitle( url, title):
                gPodderLib().deleteFilename( filename_final)
                # clear local db cache so we can re-read it
                self.ldb.clear_cache()
                self.updateComboBox()
                self.updateDownloadedComboBox()
        except:
            self.showMessage( _("Could not delete downloaded podcast."))
    #-- Gpodder.on_btnDownloadedDelete_clicked }


class Gpodderchannel(SimpleGladeApp):
    event = None
    channel = None
    podcast = None
    thread = None

    def __init__(self, path="gpodder.glade",
                 root="gPodderChannel",
                 domain=app_name, **kwargs):
        waiting = None
        url = ""
        result = False
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    #-- Gpodderchannel.new {
    def new(self):
        if libgpodder.isDebugging():
            print "A new %s has been created" % self.__class__.__name__
    #-- Gpodderchannel.new }

    #-- Gpodderchannel custom methods {
    def requestURL( self, channel = None):
        if channel != None:
            self.entryURL.set_text( channel.url)
            self.downloadTo.set_text( channel.save_dir)
            self.channel_title.set_markup( "<b>%s</b>" % channel.title)
            channel.set_metadata_from_localdb()
            self.cbNoSync.set_active( not channel.sync_to_devices)
            description = channel.description
            if channel.image != None:
                # load image in background
                gPodderLib().get_image_from_url( channel.image, self.imgCover.set_from_pixbuf, self.labelCoverStatus.set_text, self.labelCoverStatus.hide, channel.cover_file)
        else:
            self.channel_title.set_markup( "<b>%s</b>" % _("(unknown)"))
            description = _("(unknown)")
        
        b = gtk.TextBuffer()
        b.set_text( description)
        self.channel_description.set_buffer( b)
        
        self.waiting = Event()
        while self.waiting.isSet() == False:
            self.waiting.wait( 0.01)
            while gtk.events_pending():
                gtk.main_iteration( False)
        
        if self.result == True:
            if channel != None:
                channel.sync_to_devices = not self.cbNoSync.get_active()
                channel.save_metadata_to_localdb()
            return self.url
        else:
            return None
    #-- Gpodderchannel custom methods }

    #-- Gpodderchannel.on_gPodderChannel_destroy {
    def on_gPodderChannel_destroy(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_gPodderChannel_destroy called with self.%s" % widget.get_name()
        self.result = False
    #-- Gpodderchannel.on_gPodderChannel_destroy }

    #-- Gpodderchannel.on_btnOK_clicked {
    def on_btnOK_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnOK_clicked called with self.%s" % widget.get_name()
        self.url = self.entryURL.get_text()
        self.gPodderChannel.destroy()
        self.result = True

        if self.waiting != None:
            self.waiting.set()
    #-- Gpodderchannel.on_btnOK_clicked }

    #-- Gpodderchannel.on_btnCancel_clicked {
    def on_btnCancel_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnCancel_clicked called with self.%s" % widget.get_name()
        self.gPodderChannel.destroy()
        self.result = False
        
        if self.waiting != None:
            self.waiting.set()
    #-- Gpodderchannel.on_btnCancel_clicked }


class Gpodderproperties(SimpleGladeApp):
    def __init__(self, path="gpodder.glade",
                 root="gPodderProperties",
                 domain=app_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    #-- Gpodderproperties.new {
    def new(self):
        if libgpodder.isDebugging():
            print "A new %s has been created" % self.__class__.__name__
        gl = gPodderLib()
        self.httpProxy.set_text( gl.http_proxy)
        self.ftpProxy.set_text( gl.ftp_proxy)
        self.openApp.set_text( gl.open_app)
        self.iPodMountpoint.set_text( gl.ipod_mount)
        # the use proxy env vars check box
        self.cbEnvironmentVariables.set_active( gl.proxy_use_environment)
        # if the symlink exists, set the checkbox active
        self.cbDesktopSymlink.set_active( gl.getDesktopSymlink())
        # setup cell renderers
        cellrenderer = gtk.CellRendererPixbuf()
        self.comboPlayerApp.pack_start( cellrenderer, False)
        self.comboPlayerApp.add_attribute( cellrenderer, 'pixbuf', 2)
        cellrenderer = gtk.CellRendererText()
        self.comboPlayerApp.pack_start( cellrenderer, True)
        self.comboPlayerApp.add_attribute( cellrenderer, 'markup', 0)
        # end setup cell renderers
    #-- Gpodderproperties.new }

    #-- Gpodderproperties custom methods {
    def set_uar( self, uar):
        self.comboPlayerApp.set_model( uar.get_applications_as_model())
        # try to activate an item
        index = self.find_active()
        self.comboPlayerApp.set_active( index)
    # end set_uar
    
    def find_active( self):
        model = self.comboPlayerApp.get_model()
        iter = model.get_iter_first()
        index = 0
        while iter != None:
            command = model.get_value( iter, 1)
            if command == self.openApp.get_text():
                return index
            iter = model.iter_next( iter)
            index = index + 1
        # return last item = custom command
        return index-1
    # end find_active
    #-- Gpodderproperties custom methods }

    #-- Gpodderproperties.on_gPodderProperties_destroy {
    def on_gPodderProperties_destroy(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_gPodderProperties_destroy called with self.%s" % widget.get_name()
    #-- Gpodderproperties.on_gPodderProperties_destroy }

    #-- Gpodderproperties.on_comboPlayerApp_changed {
    def on_comboPlayerApp_changed(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_comboPlayerApp_changed called with self.%s" % widget.get_name()
        
        # find out which one
        iter = self.comboPlayerApp.get_active_iter()
        model = self.comboPlayerApp.get_model()
        command = model.get_value( iter, 1)
        if command == '':
            self.openApp.set_sensitive( True)
            self.openApp.show()
            self.labelCustomCommand.show()
        else:
            self.openApp.set_text( command)
            self.openApp.set_sensitive( False)
            self.openApp.hide()
            self.labelCustomCommand.hide()
    #-- Gpodderproperties.on_comboPlayerApp_changed }

    #-- Gpodderproperties.on_cbEnvironmentVariables_toggled {
    def on_cbEnvironmentVariables_toggled(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_cbEnvironmentVariables_toggled called with self.%s" % widget.get_name()
        sens = not self.cbEnvironmentVariables.get_active()
        self.httpProxy.set_sensitive( sens)
        self.ftpProxy.set_sensitive( sens)
    #-- Gpodderproperties.on_cbEnvironmentVariables_toggled }

    #-- Gpodderproperties.on_btnOK_clicked {
    def on_btnOK_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnOK_clicked called with self.%s" % widget.get_name()
        gl = gPodderLib()
        gl.http_proxy = self.httpProxy.get_text()
        gl.ftp_proxy = self.ftpProxy.get_text()
        gl.open_app = self.openApp.get_text()
        gl.proxy_use_environment = self.cbEnvironmentVariables.get_active()
        gl.ipod_mount = self.iPodMountpoint.get_text()
        gl.propertiesChanged()
        # create or remove symlink to download dir on desktop
        if self.cbDesktopSymlink.get_active():
            gl.createDesktopSymlink()
        else:
            gl.removeDesktopSymlink()
        self.gPodderProperties.destroy()
    #-- Gpodderproperties.on_btnOK_clicked }

    #-- Gpodderproperties.on_btnCancel_clicked {
    def on_btnCancel_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnCancel_clicked called with self.%s" % widget.get_name()
        self.gPodderProperties.destroy()
    #-- Gpodderproperties.on_btnCancel_clicked }


class Gpodderepisode(SimpleGladeApp):
    def __init__(self, path="gpodder.glade",
                 root="gPodderEpisode",
                 domain=app_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    #-- Gpodderepisode.new {
    def new(self):
        if libgpodder.isDebugging():
            print "A new %s has been created" % self.__class__.__name__
    #-- Gpodderepisode.new }

    #-- Gpodderepisode custom methods {
    #   Write your own methods here
    def set_episode( self, episode):
        self.episode_title.set_markup( '<big><b>%s</b></big>' % episode.title)
        b = gtk.TextBuffer()
        b.set_text( strip( episode.description))
        self.episode_description.set_buffer( b)
    #-- Gpodderepisode custom methods }

    #-- Gpodderepisode.on_btnCloseWindow_clicked {
    def on_btnCloseWindow_clicked(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_btnCloseWindow_clicked called with self.%s" % widget.get_name()
        self.gPodderEpisode.destroy()
    #-- Gpodderepisode.on_btnCloseWindow_clicked }


class Gpoddersync(SimpleGladeApp):

    def __init__(self, path="gpodder.glade",
                 root="gPodderSync",
                 domain=app_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    #-- Gpoddersync.new {
    def new(self):
        global artwork_dir
        if libgpodder.isDebugging():
            print "A new %s has been created" % self.__class__.__name__
        self.imageSyncServer.set_from_file( artwork_dir + 'computer.png')
        self.imageSyncAnimation.set_from_file( artwork_dir + 'sync-anim.gif')
        self.imageSyncClient.set_from_file( artwork_dir + 'ipod-mini.png')
    #-- Gpoddersync.new }

    #-- Gpoddersync custom methods {
    def set_progress( self, pos, max):
        self.pbSync.set_fraction( 1.0*pos/max)
        percent = _('%d of %d') % ( pos, max )
        self.pbSync.set_text( percent)

    def set_status( self, episode = None, channel = None, progressbar = None):
        if episode != None:
            self.labelEpisode.set_text( episode)

        if channel != None:
            self.labelChannel.set_text( channel)

        if progressbar != None:
            self.pbSync.set_text( progressbar)

    def close( self):
        self.gPodderSync.destroy()
    #-- Gpoddersync custom methods }

    #-- Gpoddersync.on_gPodderSync_destroy {
    def on_gPodderSync_destroy(self, widget, *args):
        if libgpodder.isDebugging():
            print "on_gPodderSync_destroy called with self.%s" % widget.get_name()
    #-- Gpoddersync.on_gPodderSync_destroy }


#-- main {

def main( __version__ = None):
    global app_version
    
    #gtk.gdk.threads_init()
    gobject.threads_init()
    bindtextdomain( app_name, locale_dir)
    app_version = __version__
    g_podder = Gpodder()
    #g_podder_channel = Gpodderchannel()
    #g_podder_properties = Gpodderproperties()
    #g_podder_episode = Gpodderepisode()
    #g_podder_sync = Gpoddersync()

    g_podder.set_icon()
    g_podder.run()

if __name__ == "__main__":
    print _("Please do not call gpodder.py directly. Instead, call the gpodder binary.")
    sys.exit( -1)

#-- main }
