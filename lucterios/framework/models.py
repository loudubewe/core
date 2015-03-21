# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals

from django.db import models
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

class LucteriosModel(models.Model):

    @classmethod
    def _get_list_fields_names(cls, current_desc, readonly):
        res = []
        for fieldname in current_desc:
            if fieldname is None:
                for subclass in cls.__bases__:
                    if issubclass(subclass, LucteriosModel):
                        res.extend(subclass.get_fields_names(readonly))
            else:
                res.append(fieldname)
        return res

    @classmethod
    def get_fields_names(cls, readonly):
        res = None
        if readonly:
            dataname = cls.__name__.lower() + '__showfields'
        else:
            dataname = cls.__name__.lower() + '__editfields'
        if hasattr(cls, dataname):
            current_desc = getattr(cls, dataname)
            if isinstance(current_desc, list):
                res = cls._get_list_fields_names(current_desc, readonly)
            elif isinstance(current_desc, dict):
                res = {}
                for (key, value) in current_desc.items():
                    res[key] = cls._get_list_fields_names(value, readonly)

        return res

    @classmethod
    def _get_list_fields_for_search(cls, current_desc):
        res = []
        for fieldname in current_desc:
            if fieldname is None:
                for subclass in cls.__bases__:
                    if issubclass(subclass, LucteriosModel):
                        res.extend(subclass.get_fieldnames_for_search())
            else:
                res.append(fieldname)
        return res

    @classmethod
    def get_fieldnames_for_search(cls):
        res = []
        dataname = cls.__name__.lower() + '__searchfields'
        if hasattr(cls, dataname):
            current_desc = getattr(cls, dataname)
            if isinstance(current_desc, list):
                res = cls._get_list_fields_for_search(current_desc)
        return res

    def can_delete(self):
        # pylint: disable=unused-argument,no-self-use
        return ''

    def edit(self, xfer):
        # pylint: disable=unused-argument,no-self-use
        return

    def show(self, xfer):
        # pylint: disable=unused-argument,no-self-use
        return

    def saving(self, xfer):
        # pylint: disable=unused-argument,no-self-use
        return

    class Meta(object):
        # pylint: disable=no-init
        abstract = True

class LucteriosSession(Session, LucteriosModel):

    default_fields = [(_('username'), 'username'), 'expire_date']

    @property
    def username(self):
        data = self.get_decoded()
        user_id = data.get('_auth_user_id', None)
        if user_id is None:
            return "---"
        else:
            return User.objects.get(id=user_id).username  # pylint: disable=no-member

    class Meta(object):
        # pylint: disable=no-init
        proxy = True
        default_permissions = []
        verbose_name = _('session')
        verbose_name_plural = _('sessions')
