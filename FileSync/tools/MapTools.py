#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin FileSync

********************************************************************

* Date                 : 2026-06-11
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

********************************************************************
"""

import qgis, os

from PyQt5.QtGui import QColor

from PyQt5 import QtCore

from PyQt5.QtWidgets import QDialog, QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox, QCheckBox

import time, math, platform, subprocess

from pathlib import Path

from FileSync.tools.MyTools import debug_log

from FileSync.tools import MyTools


class FeatureDigitizeMapTool(qgis.gui.QgsMapToolEmitPoint):
    """Digitize-Tool and File-Preview for Layers
    called from attribute-table/form via layer-action
    QgsMapToolEmitPoint, additional properties are set in runtime, because used via QgsAction from different layers
    """
    # Rev. 2025-06-11

    # animated arrow- and point-decoration with flashing grafics
    # flash-duration
    flash_total_duration_msec = 2000

    # flash-speed
    flash_interval_msec = 200

    # identify these two layer-actions to enable targeted refreshs
    georef_act_id = QtCore.QUuid('{fa3440e3-0464-431b-9c41-945d46433153}')
    show_file_act_id = QtCore.QUuid('{fa3440e3-0464-431b-9c41-945d46433154}')
    show_form_act_id = QtCore.QUuid('{fa3440e3-0464-431b-9c41-945d46433155}')

    def __init__(self, iface: qgis._gui.QgisInterface):
        """
        constructor
        :param iface: access to QGis-Application, f.e. mapCanvas, messageBar...
        """
        # Rev. 2025-06-11
        qgis.gui.QgsMapToolEmitPoint.__init__(self, iface.mapCanvas())

        self.iface = iface

        # properties for geometry-edits
        # Note: get lost if set with init, reason unknown
        # Workaround: set after init if called via QgsAction from attribute-tables or forms
        # digitize_map_tool = FeatureDigitizeMapTool(iface)
        # digitize_map_tool.layer_id = layer_id
        # digitize_map_tool.direction_field_name = direction_field_name
        # digitize_map_tool.last_edit_date_time_field_name = last_edit_date_time_field_name
        #
        # iface.mapCanvas().setMapTool(digitize_map_tool)
        # id of current edit-feature
        self.feature_id = None
        # layer id
        self.layer_id = None
        # for image-preview
        self.abs_path_field_name = None
        # for storing timestamp of last edit
        self.last_edit_date_time_field_name = None
        # for digitizing the foto-direction
        self.direction_field_name = None
        # for storing timestamp of last edit
        self.last_edit_date_time_field_name = None

        # three temporary grafics
        # show feature-location
        self.md_vm = qgis.gui.QgsVertexMarker(self.iface.mapCanvas())
        self.md_vm.setPenWidth(2)
        self.md_vm.setIconSize(15)
        self.md_vm.setIconType(4)
        self.md_vm.setColor(QColor('#FFff5050'))
        self.md_vm.hide()

        # map-move-line-graphic for interactive direction-digitize
        self.mm_rb = qgis.gui.QgsRubberBand(self.iface.mapCanvas())
        self.mm_rb.setWidth(2)
        self.mm_rb.setLineStyle(1)
        self.mm_rb.setColor(QColor('#FFff0000'))
        self.mm_rb.hide()

        # arrow-graphic to show digitize-direction
        self.arrow_rb = qgis.gui.QgsRubberBand(self.iface.mapCanvas())
        self.arrow_rb.setWidth(2)
        self.arrow_rb.setLineStyle(1)
        self.arrow_rb.setColor(QColor('#FFff0000'))
        self.arrow_rb.hide()

        # arrow-length in pixel
        self.arrow_length_px = 60

        # mouse-down-point, stored for geometry and direction created on canvasReleaseEvent
        self.md_point = None

        # these properties are stored via implemented actions in layers-Actions-properties
        # they can be altered via the implemented dialog, which then will re-implement these layer-actions
        # so it can be called from different layers/tables/forms and set these properties for a digitize-session

        # @ToThink: only once or keep MapTool and selection alive?
        # True => usetMapTool in canvasReleaseEvent => one-time-digitize
        # False => MapTool is kept until any other MapTool is triggered (f.e. pan) => any map-click afterwards will change the geometry of the last selected feature
        self.unset_after_usage = False

        # temporary symbolize point and direction
        self.flash_timer = QtCore.QTimer(self)
        self.flash_timer.setSingleShot(False)
        self.flash_timer.timeout.connect(self.do_flash)
        # flag-var to switch between flash_style/no_flash_style
        self.is_flashing = False
        # start-time in nano-seconds
        self.timer_started_ns = None

    def flags(self):
        """ disables the default-zoom-behaviour with ShiftModifier
            see: https://gis.stackexchange.com/questions/449523/override-the-zoom-behaviour-of-qgsmaptoolextent"""
        # Rev. 2025-06-13
        return super().flags() & ~qgis.gui.QgsMapToolEmitPoint.AllowZoomRect

    @staticmethod
    def open_file(abs_path: str | Path):
        """open file with default application
        :param abs_path:
        """
        # Rev. 2025-06-11
        if isinstance(abs_path, str):
            abs_path = Path(abs_path)

        try:
            if abs_path.is_file():
                # platform-dependend
                if platform.system() == 'Darwin':
                    # macOS
                    subprocess.run(('open', abs_path))
                elif platform.system() == 'Windows':
                    # Windows
                    os.startfile(abs_path)
                else:
                    # linux variants
                    # nice: only opens one instance for one file and re-focusses if its opened again
                    subprocess.call(('xdg-open', abs_path))
            else:
                pass
        except:
            pass

    def do_flash(self):
        """animated flash, toggle visibility for self.flash_total_duration_msec, called via QTimer self.flash_timer in show_feature: self.flash_timer.start(self.flash_interval_msec)"""
        # Rev. 2025-06-11
        flash_time_ns = time.perf_counter_ns() - self.timer_started_ns
        if flash_time_ns < self.flash_total_duration_msec * 1e6:
            self.arrow_rb.setVisible(not self.arrow_rb.isVisible())
            self.md_vm.setVisible(not self.md_vm.isVisible())
        else:
            # flash_total_duration_msec is reached, stop the timer and reset the style
            self.flash_timer.stop()
            self.arrow_rb.setVisible(False)
            self.md_vm.setVisible(False)

    def show_form(self, feature_id: int):
        vl = qgis._core.QgsProject.instance().mapLayer(self.layer_id)

        if vl and isinstance(vl, qgis._core.QgsVectorLayer):
            feature = vl.getFeature(feature_id)
            if feature.isValid():
                self.show_feature(feature_id,'')
                MyTools.show_feature_form(self.iface, vl, feature_id)
            else:
                self.iface.messageBar().pushMessage("ShowFile", f"Feature #{feature_id} not valid...", level=qgis._core.Qgis.Info)
        else:
            self.iface.messageBar().pushMessage("ShowFile", f"Layer '{self.layer_id}' not valid...", level=qgis._core.Qgis.Warning)

    def show_feature(self, feature_id: int, zoom_mode:str = None):
        """Show single feature on map, called from attribute-table or form or identify-result via layer-action
        implemented for point-features
        :param feature_id: ID of the feature
        :param zoom_mode: if None the zoom-mode is detected from check_mods
        """
        # Rev. 2025-06-11

        # reset animation from previous call
        self.arrow_rb.reset()
        self.flash_timer.stop()
        self.arrow_rb.setVisible(False)
        self.md_vm.setVisible(False)

        if zoom_mode is None:
            if MyTools.check_mods('n'):
                zoom_mode = 'pan'
            if MyTools.check_mods('sc'):
                zoom_mode = ''
            elif MyTools.check_mods('s'):
                # shift
                zoom_mode = 'pan_in'
            elif MyTools.check_mods('c'):
                # control
                zoom_mode = 'pan_out'
            else:
                # no modifier => pan
                zoom_mode = 'pan'

        vl = qgis._core.QgsProject.instance().mapLayer(self.layer_id)

        if vl and isinstance(vl,qgis._core.QgsVectorLayer):
            #vl.removeSelection()
            feature = vl.getFeature(feature_id)
            if feature.isValid():
                # store some metas for interactive geometry-edits, see canvas-Move/Release/Press-Event
                self.feature_id = feature_id

                #vl.select(feature_id)

                # construct temporal grafics
                if feature.hasGeometry() and not feature.geometry().isNull():
                    tr_vl_2_cvs = qgis._core.QgsCoordinateTransform(vl.crs(), self.iface.mapCanvas().mapSettings().destinationCrs(), qgis._core.QgsProject.instance())
                    feature_geom = feature.geometry()

                    # transform to canvas-crs
                    feature_geom.transform(tr_vl_2_cvs)

                    # usage here for FileSync-Point-Layers
                    # @ToThink: own plugin extended for other geometry-types
                    if vl.geometryType() == qgis._core.Qgis.GeometryType.Point:

                        # arrow to show image-direction
                        if self.direction_field_name and vl.fields().indexOf(self.direction_field_name) >= 0 and feature[self.direction_field_name] != qgis.core.NULL:
                            # check field *and* contents
                            # Note 1: GPS-direction => clockwise direction against north
                            # Note 2: GPS-Position and direction may by imprecise, especially in suboptimal reception conditions and hardware

                            dir_rad = (feature[self.direction_field_name]) / 180 * math.pi

                            # calculate arrow-size in map-units
                            arrow_length_mu = self.arrow_length_px * self.iface.mapCanvas().mapUnitsPerPixel()

                            # arrow-polygon:
                            # root-point, feature_geom with slight offset in recording direction
                            # root-triangle a b c around geometry (currently not used)
                            # Arrow axis a d
                            # Arrowhead d e f g d

                            x_0 = feature_geom.constGet().x()
                            y_0 = feature_geom.constGet().y()

                            x_a = x_0 + arrow_length_mu / 20 * math.sin(dir_rad)
                            y_a = y_0 + arrow_length_mu / 20 * math.cos(dir_rad)

                            p_a = qgis._core.QgsPointXY(x_a, y_a)

                            # root-triangle
                            # x_b = x_a + arrow_length_mu / 10 * math.sin(dir_rad - math.pi * 5 / 6)
                            # y_b = y_a + arrow_length_mu / 10 * math.cos(dir_rad - math.pi * 5 / 6)
                            # p_b = qgis._core.QgsPointXY(x_b, y_b)
                            #
                            #
                            # x_c = x_a + arrow_length_mu / 10 * math.sin(dir_rad + math.pi * 5 / 6)
                            # y_c= y_a + arrow_length_mu / 10 * math.cos(dir_rad + math.pi * 5 / 6)
                            # p_c = qgis._core.QgsPointXY(x_c, y_c)

                            x_d = x_0 + arrow_length_mu * math.sin(dir_rad)
                            y_d = y_0 + arrow_length_mu * math.cos(dir_rad)
                            p_d = qgis._core.QgsPointXY(x_d, y_d)

                            x_e = x_d + arrow_length_mu / 4 * math.sin(dir_rad + math.pi * 7 / 8)
                            y_e = y_d + arrow_length_mu / 4 * math.cos(dir_rad + math.pi * 7 / 8)
                            p_e = qgis._core.QgsPointXY(x_e, y_e)

                            x_f = x_0 + arrow_length_mu * 0.9 * math.sin(dir_rad)
                            y_f = y_0 + arrow_length_mu * 0.9 * math.cos(dir_rad)
                            p_f = qgis._core.QgsPointXY(x_f, y_f)

                            x_g = x_d + arrow_length_mu / 4 * math.sin(dir_rad - math.pi * 7 / 8)
                            y_g = y_d + arrow_length_mu / 4 * math.cos(dir_rad - math.pi * 7 / 8)
                            p_g = qgis._core.QgsPointXY(x_g, y_g)

                            # if root-triangle wanted:
                            # p_a,p_b,p_c,
                            arrow_geom = qgis._core.QgsGeometry(qgis._core.QgsLineString([p_a, p_d, p_e, p_f, p_g, p_d]))

                            self.arrow_rb.setToGeometry(arrow_geom)
                            self.arrow_rb.show()

                        self.md_vm.setCenter(feature_geom.asPoint())
                        self.md_vm.show()

                    if zoom_mode == 'pan':
                        self.iface.mapCanvas().setCenter(feature_geom.asPoint())
                        self.iface.mapCanvas().refresh()
                    elif zoom_mode == 'pan_out':
                        self.iface.mapCanvas().setCenter(feature_geom.asPoint())
                        self.iface.mapCanvas().zoomByFactor(1.25)
                        self.iface.mapCanvas().refresh()
                    elif zoom_mode == 'pan_in':
                        self.iface.mapCanvas().setCenter(feature_geom.asPoint())
                        self.iface.mapCanvas().zoomByFactor(0.8)
                        self.iface.mapCanvas().refresh()

                    self.flash_timer.start(self.flash_interval_msec)
                    self.timer_started_ns = time.perf_counter_ns()
                else:
                    self.iface.messageBar().pushMessage("ShowFeature", f"Feature #{feature_id} without geometry...", level=qgis._core.Qgis.Info)
            else:
                self.iface.messageBar().pushMessage("ShowFeature", f"Feature #{feature_id} not valid...", level=qgis._core.Qgis.Info)

    @classmethod
    def add_show_form_action(cls, vl: qgis._core.QgsVectorLayer):
        """adds or replaces a QgsAction in vector-layer to open feature-form from attribute-table
        :param vl: vector-layer, which gets the QgsAction
        """
        # Rev. 2025-06-11
        # Python-Code for the GenericPython-QgsAction
        # Note: access to Plugin-Scripts from QgsAction via plugin-install-directory inside QGis-User-Profile-Directory
        # Note 2: surrounded with try/catch if the plugin has been uninstalled but the actions persisted
        # Note 3: if action already exist, their command will be replaced

        # faked self references the loaded Plugin-Object of Type FileSync,
        # which has a property digitize_map_tool of type FeatureDigitizeMapTool
        # singleton to ensure only one instance, but usable by many layers
        # parameter [%@layer_id%] and [%@id%] come automatically when QgsAction is called

        command = f"""try:
    self = qgis.utils.plugins['FileSync']
    self.digitize_map_tool.layer_id='[%@layer_id%]'
    self.digitize_map_tool.show_form([%@id%])
except Exception as e:
    print(e)
    qgis.utils.iface.messageBar().pushMessage('Plugin missing', f'This Layer-Action requires FileSync-plugin {{e}}...', level=qgis._core.Qgis.Warning)
"""

        # delete existing actions
        action_list = [action for action in vl.actions().actions() if action.id() == cls.show_form_act_id]
        for action in action_list:
            vl.actions().removeAction(action.id())


        # add new action:
        tab = '⠀' * 3
        show_form_action = qgis._core.QgsAction(
            cls.show_form_act_id,
            qgis._core.QgsAction.ActionType.GenericPython,
            f'Show feature form',
            command,
            f'{Path(__file__).resolve().parent.parent}/icons/mActionFormView.svg',
            False,
            'Show feature form',
            # 'Feature' => open feature-form from feature-form because of attribute-tables in QgsDualView-mode
            {'Feature', 'Canvas', 'Layer'},
            ''
        )

        vl.actions().addAction(show_form_action)

        atc = vl.attributeTableConfig()
        if not atc.actionWidgetVisible():
            # qgis._core.QgsAttributeTableConfig.ButtonList / qgis._core.QgsAttributeTableConfig.DropDown
            atc.setActionWidgetStyle(qgis._core.QgsAttributeTableConfig.ButtonList)
            atc.setActionWidgetVisible(True)
            vl.setAttributeTableConfig(atc)

        vl.reload()
    @classmethod
    def add_show_file_action(cls, vl: qgis._core.QgsVectorLayer, abs_path_field_name: str = ''):
        """adds or replaces a QgsAction in vector-layer that calls qact_show_file from a global FeatureDigitizeMapTool-Object
        :param vl: vector-layer, which gets the QgsAction
        :param abs_path_field_name: field-name containing absolute-path to show image-preview, no check here if field exists
        """
        # Rev. 2025-06-11
        # Python-Code for the GenericPython-QgsAction
        # Note: access to Plugin-Scripts from QgsAction via plugin-install-directory inside QGis-User-Profile-Directory
        # Note 2: surrounded with try/catch if the plugin has been uninstalled but the actions persisted
        # Note 3: if action already exist, their command will be replaced

        # faked self references the loaded Plugin-Object of Type FileSync,
        # which has a property digitize_map_tool of type FeatureDigitizeMapTool
        # singleton to ensure only one instance, but usable by many layers
        # parameter [%@layer_id%] and [%@id%] come automatically when QgsAction is called

        command = f"""try:
    self = qgis.utils.plugins['FileSync']
    self.digitize_map_tool.layer_id='[%@layer_id%]'
    self.digitize_map_tool.abs_path_field_name='{abs_path_field_name}'
    self.digitize_map_tool.show_file([%@id%])
except Exception as e:
    print(e)
    qgis.utils.iface.messageBar().pushMessage('Plugin missing', f'This Layer-Action requires FileSync-plugin {{e}}...', level=qgis._core.Qgis.Warning)
"""

        # delete existing actions
        action_list = [action for action in vl.actions().actions() if action.id() == cls.show_file_act_id]
        for action in action_list:
            vl.actions().removeAction(action.id())

        # add new action:
        tab = '⠀' * 3
        show_file_action = qgis._core.QgsAction(
            cls.show_file_act_id,
            qgis._core.QgsAction.ActionType.GenericPython,
            f'Show file in associated application',
            command,
            f'{Path(__file__).resolve().parent.parent}/icons/preview.svg',
            False,
            'Show file',
            {'Form', 'Feature', 'Canvas', 'Layer'},
            ''
        )

        vl.actions().addAction(show_file_action)

        atc = vl.attributeTableConfig()
        if not atc.actionWidgetVisible():
            # qgis._core.QgsAttributeTableConfig.ButtonList / qgis._core.QgsAttributeTableConfig.DropDown
            atc.setActionWidgetStyle(qgis._core.QgsAttributeTableConfig.ButtonList)
            atc.setActionWidgetVisible(True)
            vl.setAttributeTableConfig(atc)

        vl.reload()

    @classmethod
    def add_show_feature_action(cls, vl: qgis._core.QgsVectorLayer, direction_field_name: str = '', last_edit_date_time_field_name: str = ''):
        """adds or replaces a QgsAction in vector-layer that calls qact_show_feature from a global FeatureDigitizeMapTool-Object
        :param vl: vector-layer, which gets the QgsAction
        :param direction_field_name: optional field to symbolize the image-direction with flashing arrow, no check here if field exists
        :param last_edit_date_time_field_name: optional field to store time of last edit, no check here if field exists
        """
        # Rev. 2025-06-11

        # pre-check actions with this show_file_act_id
        # Note: action_id is not unique!

        # first run: check existing actions and replace their command
        if vl.geometryType() == qgis._core.Qgis.GeometryType.Point:
            # Python-Code for the GenericPython-QgsAction
            # Note: access to Plugin-Scripts from QgsAction via plugin-install-directory inside QGis-User-Profile-Directory
            # Note 2: surrounded with try/catch if the plugin has been uninstalled but the actions persisted
            # Note 3: if action already exist, their command will be replaced

            # faked self references the loaded Plugin-Object of Type FileSync,
            # which has a property digitize_map_tool of type FeatureDigitizeMapTool
            # singleton to ensure only one instance, but usable by many layers
            # parameter [%@layer_id%] and [%@id%] come automatically when QgsAction is called
            command = f"""try:
    self = qgis.utils.plugins['FileSync']
    self.digitize_map_tool.layer_id='[%@layer_id%]'
    self.digitize_map_tool.direction_field_name='{direction_field_name}'
    self.digitize_map_tool.last_edit_date_time_field_name='{last_edit_date_time_field_name}'
    qgis.utils.iface.mapCanvas().setMapTool(self.digitize_map_tool)
    self.digitize_map_tool.show_feature([%@id%])
except Exception as e:
    print(e)
    qgis.utils.iface.messageBar().pushMessage('Plugin missing', f'This Layer-Action requires FileSync-plugin {{e}}...', level=qgis._core.Qgis.Warning)            
"""
            action_list = [action for action in vl.actions().actions() if action.id() == cls.georef_act_id]
            for action in action_list:
                vl.actions().removeAction(action.id())

            tab = ' ' * 3
            geo_ref_action = qgis._core.QgsAction(
                cls.georef_act_id,
                qgis._core.QgsAction.ActionType.GenericPython,
                # shown as ToolTip, markup not supported, but linebreaks
                f'Show/edit position/direction on map\n[click] → Pan\n[shift-click] → zoom-in\n[ctrl-click] → zoom-out\n[shift + ctrl-click] → Flash',
                command,
                f'{Path(__file__).resolve().parent.parent}/icons/mActionAddArrow.svg',
                False,
                'Show/edit feature-position',
                {'Form', 'Feature', 'Layer'},
                ''
            )
            vl.actions().addAction(geo_ref_action)

            atc = vl.attributeTableConfig()
            if not atc.actionWidgetVisible():
                # qgis._core.QgsAttributeTableConfig.ButtonList / qgis._core.QgsAttributeTableConfig.DropDown
                atc.setActionWidgetStyle(qgis._core.QgsAttributeTableConfig.ButtonList)
                atc.setActionWidgetVisible(True)
                vl.setAttributeTableConfig(atc)

            vl.reload()
        else:
            qgis.utils.iface.messageBar().pushMessage("ShowFeature", f"QgsAction to show or digitize geometries in layer '{vl.name()}' only available with geometry-type Point...", level=qgis._core.Qgis.Info)


    def show_file(self, feature_id: int):
        """Open single feature's file in default-app and show its position on map,
         called from attribute-table or form or identify-result via layer-action
        :param feature_id: ID of the feature
        """
        # Rev. 2025-06-11

        vl = qgis._core.QgsProject.instance().mapLayer(self.layer_id)
        if vl and isinstance(vl,qgis._core.QgsVectorLayer):
            feature = vl.getFeature(feature_id)
            if feature.isValid():
                self.show_feature(feature_id,'')

                # show file only if clicked without zoom-modifier
                # if zoom_mode == 'pan':
                if self.abs_path_field_name and vl.fields().indexOf(self.abs_path_field_name) >= 0:
                    abs_path = feature[self.abs_path_field_name]
                    if abs_path != qgis.core.NULL:
                        abs_path_posix = Path(abs_path)
                        if abs_path_posix.is_file():
                            self.open_file(abs_path_posix)
                        else:
                            self.iface.messageBar().pushMessage("ShowFile", f"Feature #{feature_id}: file '{abs_path}' not found...", level=qgis._core.Qgis.Info)
                    else:
                        self.iface.messageBar().pushMessage("ShowFile", f"Feature #{feature_id} without path...", level=qgis._core.Qgis.Info)
                else:
                    self.iface.messageBar().pushMessage("ShowFile", f"No Absolute-Path-Field registered...", level=qgis._core.Qgis.Info)
            else:
                self.iface.messageBar().pushMessage("ShowFile", f"Feature #{feature_id} not valid...", level=qgis._core.Qgis.Info)
        else:
            self.iface.messageBar().pushMessage("ShowFile", f"Layer '{self.layer_id}' not valid...", level=qgis._core.Qgis.Warning)

    def canvasPressEvent(self, event: qgis.gui.QgsMapMouseEvent) -> None:
        """default-event for QgsMapToolEmitPoint"""
        # Rev. 2025-06-11
        self.md_vm.hide()
        self.mm_rb.hide()
        self.md_point = None
        self.arrow_rb.reset()
        self.flash_timer.stop()
        self.arrow_rb.setVisible(False)

        # self.layer_id from QgsAction-Definition (semi-hard-coded in QgsAction-command)
        # self.feature_id stored in MapTool from last usage
        if self.layer_id and self.feature_id:
            vl = qgis._core.QgsProject.instance().mapLayer(self.layer_id)
            if vl and isinstance(vl,qgis._core.QgsVectorLayer):
                if vl.isEditable():
                    self.md_point = event.mapPoint()
                    self.md_vm.setCenter(event.mapPoint())
                    self.md_vm.show()
                else:
                    self.iface.messageBar().pushMessage("DigitizeFeature", f"Layer '{vl.name()}' not editable...", level=qgis._core.Qgis.Info, duration=2)

    def canvasReleaseEvent(self, event: qgis.gui.QgsMapMouseEvent) -> None:
        """default-event for QgsMapToolEmitPoint
        uses self.md_point as new feature-geometry and calculates image-direction from event.mapPoint()"""
        # Rev. 2025-06-11
        self.md_vm.hide()
        self.mm_rb.hide()


        # self.layer_id from QgsAction-Definition (semi-hard-coded in QgsAction-command)
        # self.feature_id stored in MapTool from last usage
        # self.md_point from canvasPressEvent
        if self.layer_id and self.feature_id and self.md_point:

            vl = qgis._core.QgsProject.instance().mapLayer(self.layer_id)
            if vl and isinstance(vl,qgis._core.QgsVectorLayer):
                if vl.isEditable():
                    feature = vl.getFeature(self.feature_id)

                    if feature.isValid():

                        # self.iface.messageBar().pushMessage("ShowFeature", "übernehme Geometrie und Richtung...", level=qgis._core.Qgis.Info)
                        tr_cvs_2_vl = qgis._core.QgsCoordinateTransform(self.iface.mapCanvas().mapSettings().destinationCrs(), vl.crs(), qgis._core.QgsProject.instance())

                        md_geom = qgis._core.QgsGeometry.fromPointXY(self.md_point)
                        md_geom.transform(tr_cvs_2_vl)

                        # no modifier => reposition + rotate
                        # if any modifier is checked => rotate only
                        if MyTools.check_mods('n'):
                            feature.setGeometry(md_geom)

                        md_x = md_geom.asPoint().x()
                        md_y = md_geom.asPoint().y()

                        direction = qgis.core.NULL
                        if self.direction_field_name and vl.fields().indexOf(self.direction_field_name) >= 0:
                            # calculate direction from difference md_point/event.mapPoint(), if there is a registered field
                            if self.md_point.distance(event.mapPoint()) > 0:
                                # calculate direction only, if the two points are not identical, else set to NULL

                                mu_geom = qgis._core.QgsGeometry.fromPointXY(event.mapPoint())
                                mu_geom.transform(tr_cvs_2_vl)

                                mu_x = mu_geom.asPoint().x()
                                mu_y = mu_geom.asPoint().y()

                                # @ToThink: calculate direction from canvas-coords or layer-coords?
                                x_diff = mu_x - md_x
                                y_diff = mu_y - md_y
                                # Note: - 90 beause against North = y-Axis
                                direction = (math.atan2(x_diff, y_diff) * 180 / math.pi) % 360

                            # set to NULL if mouse_down == mouse_up
                            feature[self.direction_field_name] = direction

                        if self.last_edit_date_time_field_name and vl.fields().indexOf(self.last_edit_date_time_field_name) >= 0:
                            feature[self.last_edit_date_time_field_name] = QtCore.QDateTime.currentDateTime()

                        vl.updateFeature(feature)

                        if vl.sourceCrs().isGeographic():
                            # lon/lat => more precision, decimal degrees
                            md_x_str = qgis._core.QgsCoordinateFormatter.formatX(md_x, qgis._core.QgsCoordinateFormatter.FormatDecimalDegrees, 6, qgis._core.QgsCoordinateFormatter.FlagDegreesPadMinutesSeconds)
                            md_y_str = qgis._core.QgsCoordinateFormatter.formatX(md_y, qgis._core.QgsCoordinateFormatter.FormatDecimalDegrees, 6, qgis._core.QgsCoordinateFormatter.FlagDegreesPadMinutesSeconds)

                        else:
                            md_x_str = qgis._core.QgsCoordinateFormatter.formatX(md_x, qgis._core.QgsCoordinateFormatter.FormatPair, 1)
                            md_y_str = qgis._core.QgsCoordinateFormatter.formatX(md_y, qgis._core.QgsCoordinateFormatter.FormatPair, 1)

                        # tricky:
                        # no tabs in messageBar with \t or "     " or &nbsp;
                        # solved with unicode U+2800 "Braille Pattern Blank"
                        # looks like but is no blank
                        # https://www.compart.com/en/unicode/U+2800
                        tab = '⠀' * 3
                        if direction:
                            message = f"{tab}x: {md_x_str}{tab}y: {md_y_str}{tab}dir: {direction:.0f}°"
                        else:
                            message = f"{tab}x: {md_x_str}{tab}y: {md_y_str}{tab}dir: NULL"

                        self.iface.messageBar().pushMessage(f"Feature #{self.feature_id} updated", message, level=qgis._core.Qgis.Success, duration=2)

                        # 2025-06-11T23:22:26     SUCCESS    Feature #3 updated : ⠀⠀⠀x: 319.520,9⠀⠀⠀y: 5.637.214,5⠀⠀⠀dir: 338°
                        # 2025-06-11T23:23:21     SUCCESS    Feature #2 updated : ⠀⠀⠀x: 6,436118°⠀⠀⠀y: 50,858528°⠀⠀⠀dir: 358°

                        # flash the new geometry
                        self.show_feature(self.feature_id,'')

                        if self.unset_after_usage:
                            self.iface.mapCanvas().unsetMapTool(self)
                    else:
                        self.iface.messageBar().pushMessage("ShowFeature", f"Feature #{self.feature_id} not valid")
                else:
                    self.iface.messageBar().pushMessage("ShowFeature", f"Layer '{vl.name()}' not editable...", level=qgis._core.Qgis.Info, duration=2)

        self.md_point = None

    def canvasMoveEvent(self, event: qgis.gui.QgsMapMouseEvent) -> None:
        """default-event for QgsMapToolEmitPoint
        draw direction-line from self.md_point to event.mapPoint()"""
        # Rev. 2025-06-11
        # self.layer_id and self.feature_id from last show_feature, self.md_point from canvasPressEvent
        if self.layer_id and self.feature_id and self.md_point:
            self.mm_rb.setToGeometry(qgis._core.QgsGeometry(qgis._core.QgsLineString([self.md_point, event.mapPoint()])))
