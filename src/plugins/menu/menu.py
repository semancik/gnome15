#!/usr/bin/env python
 
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+
 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as g15globals
import subprocess
import time
import os
import sys
import feedparser
import gtk
import gconf
import cairo
import traceback

# Plugin details - All of these must be provided
id="menu"
name="Menu"
description="Allows selections of any currently active screen " + \
            "through a menu on the LCD. It is activated by the " + \
            "<b>Menu</b> key on the G19, or L2 on the <b>L2</b> " + \
            "on the G15. Once activated, use the D-pad on the G19 " + \
            "or L3-L5 on the the G15 to navigate and select."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15Menu(gconf_client, gconf_key, screen)

class MenuItem():
    
    def __init__(self, page):
        self.page = page
        self.thumbnail = None

class G15Menu():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self._reload_theme()
    
    def activate(self):
        self.timer = None
        self.page = None
        self.selected = None
        self.screen.redraw(self.page)
    
    def deactivate(self):
        if self.page != None:
            self._hide_menu()
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:

            if self.page == None:            
                # Menu not active, should we activate?
                if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                    self._show_menu()
                    return True
            else:                            
                if self.screen.get_visible_page() == self.page:                    
                    if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                        self._hide_menu()
                        self.screen.applet.resched_cycle()
                        return True
                    elif g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                        i = self.items.index(self.selected)
                        i -= 1
                        if i < 0:
                            i = len(self.items) - 1
                        self.selected = self.items[i]
                        self.screen.applet.resched_cycle()
                        self.screen.redraw(self.page)
                        return True
                    elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                        i = self.items.index(self.selected)
                        i += 1
                        if i >= len(self.items):
                            i = 0
                        self.selected = self.items[i]
                        self.screen.applet.resched_cycle()
                        self.screen.redraw(self.page)
                        return True           
                    elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                        print "Selected ",self.selected.page.id
                        self.screen.raise_page(self.selected.page)
                        self.screen.applet.resched_cycle()
                        self._hide_menu()
                        return True                
                
        return False
    
    def paint(self, canvas):        
        for item in self.items:
            if item.page.thumbnail_painter != None:
                img = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.screen.height, self.screen.height)
                thumb_canvas = cairo.Context(img)
                try :
                    if item.page.thumbnail_painter(thumb_canvas, self.screen.height, True):
                        item.thumbnail = img
                except :
                    print "WARNING: Problem with painting thumbnail in %s" % item.page.id                   
                    traceback.print_exc(file=sys.stderr) 
        
        self.theme.draw(canvas, 
                        properties = {
                                      "title" : g15globals.name,
                                      "icon" : g15util.get_icon_path(self.gconf_client, "gnome-main-menu")
                                      }, 
                        attributes = {
                                      "items" : self.items,
                                      "selected" : self.selected
                                      })
        
    '''
    screen listener callbacks
    '''
    def new_page(self, page):
        self._reload_menu()
        
    def title_changed(self, page, title):
        self._reload_menu()
    
    def del_page(self, page):
        self._reload_menu()
        
    '''
    Private
    '''
    def _reload_menu(self):
        self.items = []
        for page in self.screen.pages:
            if page != self.page:
                self.items.append(MenuItem(page))
        self.selected = self.items[0]
        self.screen.redraw(self.page)
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        
    
    def _show_menu(self):        
        self.page = self.screen.new_page(self.paint, id="Menu", priority = g15screen.PRI_EXCLUSIVE)
        self._reload_menu()            
        self.screen.add_screen_change_listener(self)
    
    def _hide_menu(self):     
        self.screen.remove_screen_change_listener(self)
        self.screen.del_page(self.page)
        self.page = None