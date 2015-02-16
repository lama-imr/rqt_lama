# -*- coding: utf-8 -*-

from lama_msgs.msg import LamaObject
from lama_interfaces.core_interface import MapAgentInterface


class LamaDotGenerator(object):
    def __init__(self):
        self.iface = MapAgentInterface()

    def generate_dotcode(self, dotcode_factory):
        # TODO: here come some options (to come) changed and decide whether or
        # not self.generate should be called.
        self.graph = self.generate(dotcode_factory)
        self.dotcode = dotcode_factory.create_dot(self.graph)
        return self.dotcode

    def generate(self, dotcode_factory):
        # TODO: do not regenerate if database timestamp not changed.
        query_lama_object = LamaObject()
        query_lama_object.type = query_lama_object.VERTEX
        lama_objects = self.iface.get_lama_object_list(query_lama_object)

        graph = dotcode_factory.get_graph(simplify=False)
        for lama_object in lama_objects:
            dotcode_factory.add_node_to_graph(graph, str(lama_object.id))
            self._add_edge_to_graph(dotcode_factory, graph, lama_object)
        return graph

    def _add_edge_to_graph(self, dotcode_factory, graph, lama_object):
        query_lama_object = LamaObject()
        query_lama_object.type = query_lama_object.EDGE
        query_lama_object.references[0] = lama_object.id
        resp_lama_objects = self.iface.get_lama_object_list(query_lama_object)
        for edge in resp_lama_objects:
            style = 'solid' if edge.references[1] > 0 else 'dashed'
            color = [0.3, 0.3, 0.3] if edge.references[1] > 0 else [0, 0, 0]
            dotcode_factory.add_edge_to_graph(graph, str(lama_object.id),
                                              str(edge.references[1]),
                                              label=str(edge.id),
                                              style=style,
                                              color=color)
