# -*- coding: utf-8 -*-

from lama_interfaces.core_interface import CoreDBInterface

from .descriptor_info import DescriptorInfo


class LamaObjectBrowser(object):
    def __init__(self, id_):
        """
        Parameters
        ----------
        - id_: int, lama object id (id in the database).
        """
        self._iface = CoreDBInterface()
        self.id = id_
        self._descriptor_links = None

    @property
    def lama_object(self):
        if not self.id:
            return None
        return self._iface.get_lama_object(self.id)

    @property
    def descriptor_links(self):
        # TODO: use timestamp to reduce database access.
        self._descriptor_links = self._iface.get_descriptor_links(self.id)
        return self._descriptor_links

    def get_descriptor_info(self):
        descriptor_info = []
        for desc_link in self.descriptor_links:
            # TODO: specialize DescriptorInfo for each descriptor type and
            # call the specialized version here to get a descriptive text.
            descriptor_info.append(DescriptorInfo(desc_link))
        return descriptor_info
