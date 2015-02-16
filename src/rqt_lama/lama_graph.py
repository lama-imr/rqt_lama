# -*- coding: utf-8 -*-

from __future__ import print_function # debug

import os
import types

import rospkg
import rospy

from python_qt_binding import loadUi
from python_qt_binding.QtCore import Qt
from python_qt_binding.QtCore import QTimer
from python_qt_binding.QtCore import Signal
from python_qt_binding.QtCore import Slot
from python_qt_binding.QtGui import QGraphicsScene
from python_qt_binding.QtGui import QIcon
from python_qt_binding.QtGui import QTableWidgetItem
from python_qt_binding.QtGui import QWidget
from qt_dotgraph.pydotfactory import PydotFactory
from qt_dotgraph.dot_to_qt import DotToQtGenerator
from qt_gui_py_common.worker_thread import WorkerThread
from rqt_gui_py.plugin import Plugin

from .dotcode_map import LamaDotGenerator
from .lama_object_browser import LamaObjectBrowser


def handle_mousePressEvent(self, event):
    self._select_time = rospy.Time.now()
    self._id = int(self._label.text())
    print('_select_time: {}'.format(self._select_time)) # debug
    print('id: {}'.format(self._id)) # debug


class LamaGraph(Plugin):

    _deferred_fit_in_view = Signal()

    def __init__(self, context):
        super(LamaGraph, self).__init__(context)
        self.initialized = True
        self._nodes = {}
        self._edges = {}
        self._descriptors = {}
        self._lama_object = None
        self._options = {}
        self._selected_lama_object = None
        self._last_selected_lama_object = None

        self._update_graph_thread = WorkerThread(self._update_graph_thread_run,
                                                 self._update_graph_finished)
        self._update_descriptors_thread = WorkerThread(
            self._update_desc_thread_run,
            self._update_desc_finished)
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_map)

        self.setObjectName('LamaGraph')

        self._widget = QWidget()
        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_lama'), 'resource',
                               'LamaGraph.ui')
        loadUi(ui_file, self._widget)
        self._widget.setObjectName('LamaGraphnUi')
        # Show _widget.windowTitle on left-top of each plugin (when
        # it's set in _widget). This is useful when you open multiple
        # plugins at once. Also if you open multiple instances of your
        # plugin at once, these lines add number to make it easy to
        # tell from pane to pane.
        if context.serial_number() > 1:
            self._widget.setWindowTitle(self._widget.windowTitle() +
                                        (' ({})'.format(
                                            context.serial_number())))

        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(Qt.white)
        self._widget.graphics_view.setScene(self._scene)

        self._widget.map_update_button.setIcon(QIcon.fromTheme('view-refresh'))
        self._widget.map_update_button.setToolTip(self.tr('Refresh map'))
        self._widget.map_update_button.pressed.connect(self._update_map)

        self._widget.fit_button.setIcon(QIcon.fromTheme('zoom-original'))
        self._widget.fit_button.setToolTip(self.tr('Fit in view'))
        self._widget.fit_button.clicked.connect(self._fit_in_view)

        self._widget.rate_spin_box.valueChanged.connect(self._update_options)
        self._deferred_fit_in_view.connect(self._fit_in_view,
                                           Qt.QueuedConnection)

        self._widget.object_spin_box.valueChanged.connect(
            self._update_timestamp)

        self._widget.desc_widget.setVisible(False)

        # Add widget to the user interface
        context.add_widget(self._widget)

        # factory builds generic dotcode items
        self.dotcode_factory = PydotFactory()
        self.dotcode_generator = LamaDotGenerator()
        self.dot_to_qt = DotToQtGenerator()

        self._update_map()
        self._fit_in_view()

    def _update_graph_thread_run(self):
        # This runs in a non-gui thread, so don't access widgets here directly.
        self._update_graph(self._generate_dotcode())

    @Slot()
    def _update_graph_finished(self):
        self._scene.setBackgroundBrush(Qt.white)
        self._redraw_graph_scene()

    def _update_desc_thread_run(self):
        # This runs in a non-gui thread, so don't access widgets here directly.
        self._update_desc()

    @Slot()
    def _update_desc_finished(self):
        self._scene.setBackgroundBrush(Qt.white)
        self._redraw_desc_table()

    @Slot()
    def _fit_in_view(self):
        self._widget.graphics_view.fitInView(self._scene.itemsBoundingRect(),
                                             Qt.KeepAspectRatio)

    def _update_options(self):
        self._options['refresh_rate'] = self._widget.rate_spin_box.value()
        self._options['auto_fit'] = True
        if self._options['refresh_rate']:
            self._timer.setInterval(self._options['refresh_rate'] * 1000)
            self._timer.start()
        else:
            self._timer.stop()

    def _update_graph(self, dotcode):
        # This runs in a non-gui thread, so don't access widgets here directly.
        self._current_dotcode = dotcode
        self._nodes, self._edges = self.dot_to_qt.dotcode_to_qt_items(
            self._current_dotcode, 3)

    def _redraw_graph_scene(self):
        # Remove items in order to not garbage nodes which will be continued to
        # be used.
        for item in self._scene.items():
            self._scene.removeItem(item)
        self._scene.clear()
        for node_item in self._nodes.itervalues():
            self._scene.addItem(node_item)
            # Add a method to the instance with type.MethodType.
            node_item.mousePressEvent = types.MethodType(
                handle_mousePressEvent, node_item)
        for edge_items in self._edges.itervalues():
            for edge_item in edge_items:
                edge_item.add_to_scene(self._scene)
                # Add a method to the instance with type.MethodType.
                edge_item.mousePressEvent = types.MethodType(
                    handle_mousePressEvent, edge_item)

        self._scene.setSceneRect(self._scene.itemsBoundingRect())
        if self._options['auto_fit']:
            self._fit_in_view()

    def _redraw_desc_table(self):
        # Set object type, id and name.
        if self._lama_object:
            if self._lama_object.type == self._lama_object.VERTEX:
                type_ = 'Vertex'
            else:
                type_ = 'Edge'
            self._widget.object_and_number_label.setText(
                '{} {}'.format(type_, self._selected_lama_object))
            self._widget.name_label.setText(self._lama_object.name)
        else:
            self._widget.object_and_number_label.setText('Nothing selected')
            self._widget.name_label.setText('')


        # Fullfil descriptor table.
        self._widget.desc_table.setRowCount(0)
        if not self._descriptors:
            return
        for desc_info in self._descriptors:
            row = self._widget.desc_table.rowCount()
            self._widget.desc_table.setRowCount(row + 1)
            self._widget.desc_table.setItem(row, 0,
                                            desc_info.interface_name_item)
            self._widget.desc_table.setItem(row, 1, desc_info.id_item)
        self._widget.desc_widget.setVisible(True)

    def _update_map(self):
        if not self.initialized:
            return

        self._update_graph_thread.kill()
        self._update_descriptors_thread.kill()
        self._update_options()
        # TODO: avoid update if options did not change and force_update is not
        # set: cf. ros_pack_graph.py

        self._scene.setBackgroundBrush(Qt.lightGray)
        self._update_graph_thread.start()
        self._update_descriptors_thread.start()

    def _update_timestamp(self):
        """Update timestamps so that the spin box selection is the newest

        Also update the limit of object_spin_box.
        Also call _update_desc.
        """
        if not self.initialized:
            return

        object_id = self._widget.object_spin_box.value()
        print('spinbox: {}'.format(object_id))
        ids = []
        for node_item in self._nodes.itervalues():
            node_item._id = int(node_item._label.text())
            print('node: {}'.format(node_item._id))
            if node_item._id == object_id:
                node_item._select_time = rospy.Time.now()
                print('node select_time: {}'.format(node_item._select_time))
            else:
                node_item._select_time = rospy.Time(0)
            ids.append(node_item._id)
        for edge_items in self._edges.itervalues():
            for edge_item in edge_items:
                edge_item._id = int(edge_item._label.text())
                print('edge: {}'.format(edge_item._id))
                if edge_item._id == object_id:
                    edge_item._select_time = rospy.Time.now()
                else:
                    edge_item._select_time = rospy.Time(0)
                    print('edge select_time: {}'.format(edge_item._select_time))
                ids.append(edge_item._id)
        lowest_id = min(ids) if ids else -1
        highest_id = max(ids) if ids else 100000000
        self._widget.object_spin_box.setMinimum(lowest_id)
        self._widget.object_spin_box.setMaximum(highest_id)
        self._update_desc()

    def _update_desc(self):
        """Update the descriptor table

        The selected lama object is the one with the oldest timestamp.
        """
        if not self.initialized:
            return

        newest_timestamp = rospy.Time(0)
        for node_item in self._nodes.itervalues():
            if not hasattr(node_item, '_select_time'):
                continue
            if node_item._select_time > newest_timestamp:
                newest_timestamp = node_item._select_time
                self._selected_lama_object = node_item._id
        for edge_items in self._edges.itervalues():
            for edge_item in edge_items:
                if not hasattr(edge_item, '_select_time'):
                    print('no _select_time')
                    continue
                if edge_item._select_time > newest_timestamp:
                    newest_timestamp = edge_item._select_time
                    self._selected_lama_object = edge_item._id
        print('newest_timestamp: {}'.format(newest_timestamp)) # debug
        print('_selected_lama_object: {}'.format(self._selected_lama_object)) # debug
        if self._selected_lama_object is not None:
            obj_browser = LamaObjectBrowser(self._selected_lama_object)
            if (self._last_selected_lama_object !=
                self._selected_lama_object):
                self._lama_object = obj_browser.lama_object
            self._descriptors = obj_browser.get_descriptor_info()
            self._last_selected_lama_object = self._selected_lama_object
            # Deactivate the signal to avoid an infinite loop.
            self._widget.object_spin_box.valueChanged.disconnect()
            self._widget.object_spin_box.setValue(self._selected_lama_object)
            self._widget.object_spin_box.valueChanged.connect(
                self._update_timestamp)
        self._redraw_desc_table()


    def _generate_dotcode(self):
        # This runs in a non-gui thread, so don't access widgets here directly.
        return self.dotcode_generator.generate_dotcode(
            dotcode_factory=self.dotcode_factory)

    def shutdown_plugin(self):
        self._update_graph_thread.kill()
        self._update_descriptors_thread.kill()
