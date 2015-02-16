# -*- coding: utf-8 -*-

from python_qt_binding.QtGui import QTableWidgetItem


class DescriptorInfo(object):
    """Provide some textual information about a descriptor"""
    def __init__(self, descriptor_link):
        self.id = descriptor_link.descriptor_id
        self.interface_name = descriptor_link.interface_name
        self.type = ''
        self.text = ''

    @property
    def id_item(self):
        """The id as QTableWidgetItem"""
        return QTableWidgetItem(str(self.id))

    @property
    def interface_name_item(self):
        """The interface_name as QTableWidgetItem"""
        return QTableWidgetItem(self.interface_name)

    @property
    def type_item(self):
        return QTableWidgetItem(self.type)

    @property
    def text_item(self):
        return QTableWidgetItem(self.text)
