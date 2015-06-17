#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
'''
GUI tool to manage Lucterios instance

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals
from lucterios.install.lucterios_admin import LucteriosGlobal, LucteriosInstance, \
    get_module_title
from django.utils import six
from django.utils.translation import ugettext
from subprocess import Popen, PIPE, STDOUT, check_output, CalledProcessError
import sys
from time import sleep
from traceback import print_exc
from threading import Thread
import os
from lucterios.framework.settings import fill_appli_settings

FIRST_HTTP_PORT = 8100
if 'FIRST_HTTP_PORT' in os.environ.keys():
    FIRST_HTTP_PORT = os.environ['FIRST_HTTP_PORT']

READLONY = 'readonly'
VALUES = 'values'

try:
    from tkinter import Toplevel, Tk, ttk, Label, Entry, Frame, Button, Listbox, Text, StringVar
    from tkinter import E, W, N, S, END, NORMAL, DISABLED, EXTENDED
    from tkinter.messagebox import showerror, askokcancel
except ImportError:
    from Tkinter import Toplevel, Tk, Label, Entry, Frame, Button, Listbox, Text, StringVar
    from Tkinter import E, W, N, S, END, NORMAL, DISABLED, EXTENDED
    from tkMessageBox import showerror, askokcancel
    import ttk

class RunException(Exception):
    pass

def ProvideException(func):
    def wrapper(*args):
        try:
            return func(*args)
        except Exception as e:  # pylint: disable=broad-except
            print_exc()
            showerror(ugettext("View generator"), e)
    return wrapper

def ThreadRun(func):
    def wrapper(*args):
        @ProvideException
        def sub_fct():
            args[0].enabled(False)
            try:
                return func(*args)
            finally:
                args[0].enabled(True)
        Thread(target=sub_fct).start()
    return wrapper

class RunServer(object):

    def __init__(self, instance_name, port):
        self.instance_name = instance_name
        self.port = port
        self.process = None
        self.out = None

    def start(self):
        self.stop()
        cmd = [sys.executable, 'manage_%s.py' % self.instance_name, 'runserver', '--noreload', '--traceback', '0.0.0.0:%d' % self.port]
        self.process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        sleep(3.0)
        if self.process.poll() is not None:
            message = self.process.communicate()[0].decode('ascii')
            self.stop()
            raise RunException(message)
        self.open_url()

    def _search_browser_from_nix(self):
        # pylint: disable=no-self-use
        browsers = ["xdg-open", "firefox", "chromium-browser", "mozilla", "konqueror", "opera", "epiphany", "netscape"]
        browser = None
        try:
            for browser_iter in browsers:
                try:
                    val = check_output(["which", browser_iter], timeout=1)
                    if val != '':
                        browser = browser_iter
                        break
                except CalledProcessError:
                    pass
            if browser is None:
                raise RunException(ugettext("Web browser unknown!"))
            return browser
        except Exception:
            print_exc()
            raise RunException(ugettext("Web browser not found!"))

    def open_url(self):
        url = "http://127.0.0.1:%d" % self.port
        os_name = sys.platform
        if 'darwin' in os_name:
            args = ["open", url]
        elif 'win' in os_name:
            args = ["rundll32", "url.dll", "FileProtocolHandler", url]
        else:
            args = [self._search_browser_from_nix(), url]
        Popen(args)

    def stop(self):
        if self.is_running():
            self.process.terminate()
        self.process = None
        self.out = None

    def is_running(self):
        return (self.process is not None) and (self.process.poll() is None)

def center(root, size=None):
    root.update_idletasks()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    if size is None:
        size = tuple(int(_) for _ in root.geometry().split('+')[0].split('x'))
    pos_x = int(width / 2 - size[0] / 2)
    pos_y = int(height / 2 - size[1] / 2)
    root.geometry("%dx%d+%d+%d" % (size + (pos_x, pos_y)))

class InstanceEditor(Toplevel):
    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        Toplevel.__init__(self)
        self.result = None
        self.module_data = None
        self.mod_applis = None
        self.title(ugettext("Instance editor"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.ntbk = ttk.Notebook(self)
        self.ntbk.grid(row=0, column=0, columnspan=1, sticky=(N, S, E, W))

        self.frm_general = Frame(self.ntbk, width=350, height=150)
        self.frm_general.grid_columnconfigure(0, weight=0)
        self.frm_general.grid_columnconfigure(1, weight=1)
        self._general_tabs()
        self.ntbk.add(self.frm_general, text=ugettext('General'))

        self.frm_database = Frame(self.ntbk, width=350, height=150)
        self.frm_database.grid_columnconfigure(0, weight=0)
        self.frm_database.grid_columnconfigure(1, weight=1)
        self._database_tabs()
        self.ntbk.add(self.frm_database, text=ugettext('Database'))

        btnframe = Frame(self, bd=1)
        btnframe.grid(row=1, column=0, columnspan=1)
        Button(btnframe, text=ugettext("Cancel"), width=10, command=self.destroy).grid(row=0, column=0, sticky=(N, S, W))
        Button(btnframe, text=ugettext("OK"), width=10, command=self.apply).grid(row=0, column=1, sticky=(N, S, E))

    def _database_tabs(self):
        Label(self.frm_database, text=ugettext("Type")).grid(row=0, column=0, sticky=(N, W), padx=5, pady=3)
        self.typedb = ttk.Combobox(self.frm_database, textvariable=StringVar(), state=READLONY)
        self.typedb.bind("<<ComboboxSelected>>", self.typedb_selection)
        self.typedb.grid(row=0, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_database, text=ugettext("Name")).grid(row=1, column=0, sticky=(N, W), padx=5, pady=3)
        self.namedb = Entry(self.frm_database)
        self.namedb.grid(row=1, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_database, text=ugettext("User")).grid(row=2, column=0, sticky=(N, W), padx=5, pady=3)
        self.userdb = Entry(self.frm_database)
        self.userdb.grid(row=2, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_database, text=ugettext("Password")).grid(row=3, column=0, sticky=(N, W), padx=5, pady=3)
        self.pwddb = Entry(self.frm_database)
        self.pwddb.grid(row=3, column=1, sticky=(N, S, E, W), padx=5, pady=3)

    def _general_tabs(self):
        Label(self.frm_general, text=ugettext("Name")).grid(row=0, column=0, sticky=(N, W), padx=5, pady=3)
        self.name = Entry(self.frm_general)
        self.name.grid(row=0, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_general, text=ugettext("Appli")).grid(row=1, column=0, sticky=(N, W), padx=5, pady=3)
        self.applis = ttk.Combobox(self.frm_general, textvariable=StringVar(), state=READLONY)
        self.applis.bind("<<ComboboxSelected>>", self.appli_selection)
        self.applis.grid(row=1, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_general, text=ugettext("Modules")).grid(row=2, column=0, sticky=(N, W), padx=5, pady=3)
        self.modules = Listbox(self.frm_general, selectmode=EXTENDED)
        self.modules.configure(exportselection=False)
        self.modules.grid(row=2, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_general, text=ugettext("CORE-connectmode")).grid(row=3, column=0, sticky=(N, W), padx=5, pady=3)
        self.mode = ttk.Combobox(self.frm_general, textvariable=StringVar(), state=READLONY)
        self.mode.bind("<<ComboboxSelected>>", self.mode_selection)
        self.mode.grid(row=3, column=1, sticky=(N, S, E, W), padx=5, pady=3)
        Label(self.frm_general, text=ugettext("Password")).grid(row=4, column=0, sticky=(N, W), padx=5, pady=3)
        self.password = Entry(self.frm_general, show="*")
        self.password.grid(row=4, column=1, sticky=(N, S, E, W), padx=5, pady=3)

    def typedb_selection(self, event):
        # pylint: disable=unused-argument
        visible = list(self.typedb[VALUES]).index(self.typedb.get()) != 0
        for child_cmp in self.frm_database.winfo_children()[2:]:
            if visible:
                child_cmp.config(state=NORMAL)
            else:
                child_cmp.config(state=DISABLED)

    def appli_selection(self, event):
        # pylint: disable=unused-argument
        appli_id = list(self.applis[VALUES]).index(self.applis.get())
        mod_depended = self.mod_applis[appli_id][2]
        self.modules.select_clear(0, self.modules.size())
        for mod_idx in range(len(self.module_data)):
            current_mod = self.module_data[mod_idx]
            if current_mod in mod_depended:
                self.modules.selection_set(mod_idx)

    def mode_selection(self, event):
        # pylint: disable=unused-argument
        visible = list(self.mode[VALUES]).index(self.mode.get()) != 2
        for child_cmp in self.frm_general.winfo_children()[-2:]:
            if visible:
                child_cmp.config(state=NORMAL)
            else:
                child_cmp.config(state=DISABLED)

    def apply(self):
        if self.name.get() != '':
            db_param = "%s:name=%s,user=%s,password=%s" % (self.typedb.get(), self.namedb.get(), self.userdb.get(), self.pwddb.get())

            security = "MODE=%s" % list(self.mode[VALUES]).index(self.mode.get())
            if self.password.get() != '':
                security += ",PASSWORD=%s" % self.password.get()
            module_list = [self.module_data[int(item)] for item in self.modules.curselection()]
            appli_id = list(self.applis[VALUES]).index(self.applis.get())

            self.result = (self.name.get(), self.mod_applis[appli_id][0], ",".join(module_list), security, db_param)
            self.destroy()
        else:
            showerror(ugettext("Instance editor"), ugettext("Name empty!"))

    def _load_current_data(self, instance_name):
        lct_inst = LucteriosInstance(instance_name)
        lct_inst.read()
        self.name.delete(0, END)
        self.name.insert(0, lct_inst.name)
        self.name.config(state=DISABLED)
        applis_id = 0
        for appli_iter in range(len(self.mod_applis)):
            if self.mod_applis[appli_iter][0] == lct_inst.appli_name:
                applis_id = appli_iter
                break
        self.applis.current(applis_id)
        if lct_inst.extra['']['mode'] is not None:
            self.mode.current(lct_inst.extra['']['mode'][0])
        else:
            self.mode.current(2)
        self.mode_selection(None)
        typedb_index = 0
        for typedb_idx in range(len(self.typedb[VALUES])):
            if self.typedb[VALUES][typedb_idx].lower() == lct_inst.database[0].lower():
                typedb_index = typedb_idx
                break
        self.typedb.current(typedb_index)
        self.typedb.config(state=DISABLED)
        self.typedb_selection(None)
        self.namedb.delete(0, END)
        if 'name' in lct_inst.database[1].keys():
            self.namedb.insert(0, lct_inst.database[1]['name'])
        self.userdb.delete(0, END)
        if 'user' in lct_inst.database[1].keys():
            self.userdb.insert(0, lct_inst.database[1]['user'])
        self.pwddb.delete(0, END)
        if 'password' in lct_inst.database[1].keys():
            self.pwddb.insert(0, lct_inst.database[1]['password'])
        self.modules.select_clear(0, self.modules.size())
        for mod_idx in range(len(self.module_data)):
            current_mod = self.module_data[mod_idx]
            if current_mod in lct_inst.modules:
                self.modules.select_set(mod_idx)

    def execute(self, instance_name=None):
        self.mode[VALUES] = [ugettext("CORE-connectmode.0"), ugettext("CORE-connectmode.1"), ugettext("CORE-connectmode.2")]
        self.typedb[VALUES] = ["SQLite", "MySQL", "PostgreSQL"]
        lct_glob = LucteriosGlobal()
        _, self.mod_applis, mod_modules = lct_glob.installed()
        self.modules.delete(0, END)
        self.module_data = []
        for mod_module_item in mod_modules:
            self.modules.insert(END, get_module_title(mod_module_item[0]))
            self.module_data.append(mod_module_item[0])
        appli_list = []
        for mod_appli_item in self.mod_applis:
            appli_list.append(get_module_title(mod_appli_item[0]))
        self.applis[VALUES] = appli_list
        if instance_name is not None:
            self._load_current_data(instance_name)
        else:
            self.typedb.current(0)
            self.mode.current(2)
            if len(appli_list) > 0:
                self.applis.current(0)
            self.appli_selection(None)
            self.mode_selection(None)
            self.typedb_selection(None)
        center(self)

class LucteriosMainForm(Tk):

    def __init__(self):
        Tk.__init__(self)
        self.has_checked = False
        self.title(ugettext("Lucterios installer"))
        self.minsize(475, 260)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.running_instance = {}
        self.resizable(True, True)

        self.ntbk = ttk.Notebook(self)
        self.ntbk.grid(row=0, column=0, columnspan=1, sticky=(N, S, E, W))

        self.create_instance_panel()
        self.create_module_panel()

        self.btnframe = Frame(self, bd=1)
        self.btnframe.grid(row=1, column=0, columnspan=1)
        Button(self.btnframe, text=ugettext("Refresh"), width=10, command=self.refresh).grid(row=0, column=0, sticky=(N, S))
        self.btnupgrade = Button(self.btnframe, text=ugettext("No upgrade"), width=10, command=self.upgrade)
        self.set_ugrade_state(False)
        self.btnupgrade.grid(row=0, column=1, sticky=(N, S))
        Button(self.btnframe, text=ugettext("Close"), width=10, command=self.destroy).grid(row=0, column=2, sticky=(N, S))

    def destroy(self):
        instance_names = self.running_instance.keys()
        for old_item in instance_names:
            if self.running_instance[old_item] is not None:
                self.running_instance[old_item].stop()
                del self.running_instance[old_item]
        Tk.destroy(self)

    def create_instance_panel(self):
        frm_inst = Frame(self.ntbk)
        frm_inst.grid_columnconfigure(0, weight=1)
        frm_inst.grid_rowconfigure(0, weight=1)
        frm_inst.grid_columnconfigure(1, weight=3)
        frm_inst.grid_rowconfigure(1, weight=0)
        self.instance_list = Listbox(frm_inst, width=20)
        self.instance_list.bind('<<ListboxSelect>>', self.select_instance)
        self.instance_list.pack()
        self.instance_list.grid(row=0, column=0, sticky=(N, S, W, E))

        self.instance_txt = Text(frm_inst, width=75)
        self.instance_txt.grid(row=0, column=1, rowspan=2, sticky=(N, S, W, E))
        self.instance_txt.config(state=DISABLED)

        self.btninstframe = Frame(frm_inst, bd=1)
        self.btninstframe.grid(row=1, column=0, columnspan=1)
        self.btninstframe.grid_columnconfigure(0, weight=1)
        Button(self.btninstframe, text=ugettext("Launch"), width=15, command=self.open_inst).grid(row=0, column=0, sticky=(N, S))
        Button(self.btninstframe, text=ugettext("Modify"), width=15, command=self.modify_inst).grid(row=1, column=0, sticky=(N, S))
        Button(self.btninstframe, text=ugettext("Delete"), width=15, command=self.delete_inst).grid(row=2, column=0, sticky=(N, S))
        Button(self.btninstframe, text=ugettext("Add"), width=15, command=self.add_inst).grid(row=3, column=0, sticky=(N, S))

        self.ntbk.add(frm_inst, text=ugettext('Instances'))

    def create_module_panel(self):
        frm_mod = Frame(self.ntbk)
        frm_mod.grid_columnconfigure(0, weight=1)
        frm_mod.grid_rowconfigure(0, weight=1)
        self.module_txt = Text(frm_mod)
        self.module_txt.grid(row=0, column=0, sticky=(N, S, W, E))
        self.module_txt.config(state=DISABLED)
        self.ntbk.add(frm_mod, text=ugettext('Modules'))

    def enabled(self, is_enabled, widget=None):
        if widget is None:
            widget = self
        if isinstance(widget, Button) and (widget != self.btnupgrade):
            if is_enabled:
                widget.config(state=NORMAL)
            else:
                widget.config(state=DISABLED)
        else:
            for child_cmp in widget.winfo_children():
                self.enabled(is_enabled, child_cmp)

    @ThreadRun
    def refresh(self, instance_name=None):
        if instance_name is None:
            instance_name = self.get_selected_instance_name()
        self.instance_txt.delete("1.0", END)
        self._refresh_instance_list()
        self.set_select_instance_name(instance_name)
        if not self.has_checked:
            self._refresh_modules()

    def _refresh_modules(self):
        self.set_ugrade_state(False)
        self.module_txt.delete("1.0", END)
        lct_glob = LucteriosGlobal()
        mod_lucterios, mod_applis, mod_modules = lct_glob.installed()
        self.module_txt.config(state=NORMAL)
        self.module_txt.insert(END, ugettext("Lucterios core\t\t%s\n") % mod_lucterios[1])
        self.module_txt.insert(END, '\n')
        self.module_txt.insert(END, ugettext("Application\n"))
        for appli_item in mod_applis:
            self.module_txt.insert(END, "\t%s\t%s\n" % (appli_item[0].ljust(30), appli_item[1]))
        self.module_txt.insert(END, ugettext("Modules\n"))
        for module_item in mod_modules:
            self.module_txt.insert(END, "\t%s\t%s\n" % (module_item[0].ljust(30), module_item[1]))
        self.module_txt.config(state=DISABLED)
        self.has_checked = True

        self.after(1000, lambda: Thread(target=self.check).start())

    def _refresh_instance_list(self):
        self.instance_list.delete(0, END)
        luct_glo = LucteriosGlobal()
        instance_list = luct_glo.listing()
        for item in instance_list:
            self.instance_list.insert(END, item)
            if not item in self.running_instance.keys():
                self.running_instance[item] = None

        instance_names = self.running_instance.keys()
        for old_item in instance_names:
            if not old_item in instance_list:
                if self.running_instance[old_item] is not None:
                    self.running_instance[old_item].stop()
                del self.running_instance[old_item]

    def set_select_instance_name(self, instance_name):
        cur_sel = 0
        for sel_iter in range(self.instance_list.size()):
            if self.instance_list.get(sel_iter) == instance_name:
                cur_sel = sel_iter
                break
        self.instance_list.selection_set(cur_sel)
        self.select_instance(None)

    def get_selected_instance_name(self):
        if len(self.instance_list.curselection()) > 0:
            return self.instance_list.get(int(self.instance_list.curselection()[0]))
        else:
            return ""

    def set_ugrade_state(self, must_upgrade):
        if must_upgrade:
            self.btnupgrade.config(state=NORMAL)
            self.btnupgrade["text"] = ugettext("Upgrade needs")
        else:
            self.btnupgrade["text"] = ugettext("No upgrade")
            self.btnupgrade.config(state=DISABLED)

    def check(self):
        must_upgrade = False
        try:
            lct_glob = LucteriosGlobal()
            _, must_upgrade = lct_glob.check()
        finally:
            self.after(300, self.set_ugrade_state, must_upgrade)

    @ThreadRun
    def upgrade(self):
        self.btnupgrade.config(state=DISABLED)
        self.instance_list.config(state=DISABLED)
        try:
            lct_glob = LucteriosGlobal()
            lct_glob.update()
            self._refresh_modules()
        finally:
            self.btnupgrade.config(state=NORMAL)
            self.instance_list.config(state=NORMAL)

    @ThreadRun
    def select_instance(self, evt):
        # pylint: disable=unused-argument
        if self.instance_list['state'] == NORMAL:
            self.instance_list.config(state=DISABLED)
            try:
                instance_name = self.get_selected_instance_name()
                if not instance_name in self.running_instance.keys():
                    self.running_instance[instance_name] = None
                inst = LucteriosInstance(instance_name)
                inst.read()

                self.instance_txt.configure(state=NORMAL)
                self.instance_txt.delete("1.0", END)
                self.instance_txt.insert(END, "\t\t\t%s\n\n" % inst.name)
                self.instance_txt.insert(END, ugettext("Database\t\t%s\n") % inst.get_database_txt())
                self.instance_txt.insert(END, ugettext("Appli\t\t%s\n") % inst.get_appli_txt())
                self.instance_txt.insert(END, ugettext("Modules\t\t%s\n") % inst.get_module_txt())
                self.instance_txt.insert(END, ugettext("Extra\t\t%s\n") % inst.get_extra_txt())
                self.instance_txt.insert(END, '\n')
                if self.running_instance[instance_name] is not None and self.running_instance[instance_name].is_running():
                    self.instance_txt.insert(END, ugettext("=> Running in http://127.0.0.1:%s\n") % six.text_type(self.running_instance[instance_name].port))
                    self.btninstframe.winfo_children()[0]["text"] = ugettext("Stop")
                else:
                    self.running_instance[instance_name] = None
                    self.instance_txt.insert(END, ugettext("=> Stopped\n"))
                    self.btninstframe.winfo_children()[0]["text"] = ugettext("Launch")
                self.instance_txt.configure(state=DISABLED)
            finally:
                self.instance_list.config(state=NORMAL)

    @ThreadRun
    def add_modif_inst_result(self, result, to_create):
        inst = LucteriosInstance(result[0])
        inst.set_extra("")
        inst.set_appli(result[1])
        inst.set_module(result[2])
        inst.set_database(result[4])
        if to_create:
            inst.add()
        else:

            inst.modif()
        inst = LucteriosInstance(result[0])
        inst.set_extra(result[3])
        inst.security()
        self.refresh(result[0])

    def add_inst(self):
        self.enabled(False)
        try:

            ist_edt = InstanceEditor()
            ist_edt.execute()
            self.wait_window(ist_edt)
        finally:
            self.enabled(True)

        if ist_edt.result is not None:
            self.add_modif_inst_result(ist_edt.result, True)

    def modify_inst(self):
        self.enabled(False)
        try:

            ist_edt = InstanceEditor()
            ist_edt.execute(self.get_selected_instance_name())
            self.wait_window(ist_edt)
        finally:
            self.enabled(True)

        if ist_edt.result is not None:
            self.add_modif_inst_result(ist_edt.result, False)

    @ThreadRun
    def delete_inst_name(self, instance_name):
        inst = LucteriosInstance(instance_name)
        inst.delete()

        self.refresh()

    def delete_inst(self):
        instance_name = self.get_selected_instance_name()
        if askokcancel(None, ugettext("Do you want to delete '%s'?") % instance_name):
            self.delete_inst_name(instance_name)

    @ThreadRun
    def open_inst(self):
        instance_name = self.get_selected_instance_name()
        try:
            if not instance_name in self.running_instance.keys():
                self.running_instance[instance_name] = None
            if self.running_instance[instance_name] is None:
                port = FIRST_HTTP_PORT
                for inst_obj in self.running_instance.values():
                    if (inst_obj is not None) and (inst_obj.port >= port):
                        port = inst_obj.port + 1
                self.running_instance[instance_name] = RunServer(instance_name, port)
                self.running_instance[instance_name].start()
            else:
                self.running_instance[instance_name].stop()
                self.running_instance[instance_name] = None
        finally:
            self.select_instance(None)

    def execute(self):
        self.refresh()

        center(self, (700, 300))
        self.mainloop()

def main():
    import imp
    module = imp.new_module("default_setting")
    setattr(module, '__file__', "")
    setattr(module, 'SECRET_KEY', "default_setting")
    fill_appli_settings("lucterios.standard", None, module)
    sys.modules["default_setting"] = module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "default_setting")
    import django
    django.setup()
    lct_form = LucteriosMainForm()
    lct_form.execute()

if __name__ == '__main__':
    main()
