#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin FileSync
* customized QtWidgets

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


import re
import locale
import qgis
from typing import Any
from PyQt5 import QtCore, QtGui, QtWidgets

locale.setlocale(locale.LC_ALL, '')
# sets the locale for all categories to the user’s default setting

from FileSync.settings.constants import Qt_Roles

class QGroupBoxExpandable(QtWidgets.QGroupBox):
    """QGroupBox with toggle-functionality"""
    # Rev. 2025-06-22
    _min_height = 20
    _max_height = 12345

    def __init__(self, title=None, initially_opened: bool = False, parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setStyle(self.GroupBoxProxyStyle())
        self.toggled.connect(self.s_toggle)
        # there seems to be some ugly internal used styleSheet for QGroupBox with bold font and not left-aligned
        self.setStyleSheet("QGroupBox { font-weight: Normal; } ")
        if initially_opened:
            self.setChecked(True)
            self.setMaximumHeight(self._max_height)
        else:
            self.setChecked(False)
            self.setMaximumHeight(self._min_height)

    class GroupBoxProxyStyle(QtWidgets.QProxyStyle):
        """QProxyStyle to make QGroupbox expandable
        see:
        https://stackoverflow.com/questions/55977559/changing-qgroupbox-checkbox-visual-to-an-expander
        """

        def drawPrimitive(self, element, option, painter, widget):
            if element == QtWidgets.QStyle.PE_IndicatorCheckBox and isinstance(widget, QtWidgets.QGroupBox):
                if widget.isChecked():
                    super().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowDown, option, painter, widget)
                else:
                    super().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowRight, option, painter, widget)
            else:
                super().drawPrimitive(element, option, painter, widget)

    def s_toggle(self, status):
        """Toggle Group-Box in Dialog
        :param status: isChecked()-State
        """

        if status:
            self.setMaximumHeight(self._max_height)
        else:
            self.setMaximumHeight(self._min_height)


class QtbToggleGridRows(QtWidgets.QToolButton):
    """Tool-button inside QGridLayout with toggle-functionality for rectangular area of the QGridLayout"""
    # Rev. 2025-06-22
    def __init__(self, grid_elem, start_row:int, end_row:int, initially_open:bool = True):
        """
        constructor
        :param grid_elem: Element with Grid-Layout
        :param start_row: Toggle-Area starts at row
        :param end_row: Toggle-Area ends at row
        :param initially_open: Toggle-Area is initially visible
        """
        super().__init__()
        self.grid_elem = grid_elem
        self.start_row = start_row
        self.end_row = end_row
        self.grid_rows_visible = initially_open

        # style the icon
        self.setFixedSize(20, 20)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        # QToolButton::hover {background-color: silver;}
        self.setStyleSheet("QToolButton { border: 1px solid transparent;}")
        # ToolButtonIconOnly
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)


        # Icons via UTF-8-Character to symbolize the toggle-state
        self.text_is_open = '▼'
        self.text_is_closed = '▶'

        if initially_open:
            self.setText(self.text_is_open)
        else:
            self.setText(self.text_is_closed)

        self.pressed.connect(self.toggle_grid_rows)

    def toggle_grid_rows(self,grid_rows_visible:bool = None):
        """click-function which toggles visibility for rows in self.grid_elem from self.start_row to self.end_row
        :param grid_rows_visible: if None, the current grid_rows_visible will be toggled
        """
        if grid_rows_visible is not None:
            self.grid_rows_visible = grid_rows_visible
        else:
            self.grid_rows_visible = not self.grid_rows_visible


        if self.start_row < self.grid_elem.layout().rowCount():
            for sub_row in range(self.start_row, self.end_row):
                if sub_row < self.grid_elem.layout().rowCount():
                    for sub_col in range(self.grid_elem.layout().columnCount()):
                        # https://doc.qt.io/archives/qt-5.15/qlayoutitem.html
                        qli = self.grid_elem.layout().itemAtPosition(sub_row, sub_col)
                        if qli:
                            qli.widget().setVisible(self.grid_rows_visible)

        if self.grid_rows_visible:
            self.setText(self.text_is_open)
        else:
            self.setText(self.text_is_closed)



class MyQComboBox(QtWidgets.QComboBox):
    """derived QComboBox for special purposes"""
    # Rev. 2025-06-22

    def __init__(self, parent, column_pre_settings: list, option_text_template: str = '{0}', show_clear_button: bool = False):
        """
        constructor
        :param parent: Qt-Hierarchy
        :param column_pre_settings: metadata for colums in QTableView
        :param option_text_template: Template for QLineEdit
        :param show_clear_button: show a button to clear current selected item
        :param show_disabled: True => disabled items are listed, False (default): disabled items are not listed making the list clearer
        """
        # Rev. 2025-06-22

        super().__init__(parent)

        self.column_settings = column_pre_settings
        self.option_text_template = option_text_template
        self.show_clear_button = show_clear_button

        #self.clear_button_icon = self.style().standardIcon(70)
        # optinally define own icon:
        self.clear_button_icon = None

        self.setModel(QtGui.QStandardItemModel())

        self.resize_mode = 'resize_to_contents'
        self.calc_width = 0
        self.calc_height = 0

        self.fix_width = 600
        self.fix_height = 800

        # via handle resizable size
        self.pop_up_width = None
        self.pop_up_height = None



        self.view_tool_tip = None

        self.setView(QtWidgets.QTableView(self))

        # row-wise select
        self.view().setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # some default-settings
        self.view().setShowGrid(True)
        self.view().setSortingEnabled(True)
        self.view().setWordWrap(False)
        self.view().setTextElideMode(QtCore.Qt.ElideRight)
        self.view().horizontalHeader().show()
        self.view().verticalHeader().hide()
        self.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.view().setMinimumHeight(100)
        self.view().setMinimumWidth(200)


        pop_up_frame = self.findChild(QtWidgets.QFrame)


        # size-grip in bottom/right corner
        self.qsgr = QtWidgets.QSizeGrip(self)
        self.qsgr.setStyleSheet("QSizeGrip {background-color: silver; width: 10px; height: 10px;}")

        self.qsgr.mouseReleaseEvent = self.release_size_grip

        #QBoxLayout
        pop_up_frame.layout().addWidget(self.qsgr,0,QtCore.Qt.AlignRight)

        # self.view().verticalHeader().setMinimumSectionSize(20)
        # self.view().verticalHeader().setMaximumSectionSize(20)
        self.view().verticalHeader().setDefaultSectionSize(20)



        # ResizeMode-enum :
        # Interactive -> 0 cols can be resized by user, initial size as defined in col_widths
        # Stretch -> 1 cols will be stretched to the width of the QtWidgets.QComboBox -> width of QtWidgets.QTableView == width of QCombBox
        # Fixed -> 2 fix defined widths, width of QtWidgets.QTableView = sum(col_widths)
        # ResizeToContents -> 3 cols will be stretched to their contents -> width of QtWidgets.QTableView = sum(calculated col_widths) + x

        self.view().horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.view().horizontalHeader().setStretchLastSection(True)

        # Breite/Höhe der Icons in QStandardItems, falls diese überhaupt verwendet werden,
        # nicht des ClearButtons
        self.setIconSize(QtCore.QSize(15, 15))

        if self.show_clear_button:
            self.setLineEdit(QtWidgets.QLineEdit())
            self.lineEdit().setClearButtonEnabled(True)
            self.lineEdit().setReadOnly(True)
            self.lineEdit().setFont(self.font())
            # convenience: Click on lineEdit with same popuo-functionality as klick on drop-down-button
            self.lineEdit().mousePressEvent = self.show_popup

            clear_button = self.lineEdit().findChild(QtWidgets.QToolButton)
            # note: to show a blank LineEdit if nothing is selected the model needs a blank row in model-data
            clear_button.clicked.connect(lambda: self.setCurrentIndex(-1))
            # enable clear_button in an readOnly == disabled lineEdit()
            clear_button.setEnabled(True)
            # clear_button_icon applied with set_model

    def release_size_grip(self,evt: QtGui.QMouseEvent):
        """re-implemented mouseReleaseEvent for the QSizeGrip
        stores the resized format for later restore in showPopup"""
        pop_up_frame = self.findChild(QtWidgets.QFrame)
        self.pop_up_width = pop_up_frame.width()
        self.pop_up_height = pop_up_frame.height()

        QtWidgets.QSizeGrip.mouseReleaseEvent(self.qsgr,evt)


    def set_model(self, in_model: QtGui.QStandardItemModel):
        """loads model-data and applies some visual settings f.e. headers and tool_tips, width/height/position of
        :param in_model:"""
        # Rev. 2025-02-01
        with QtCore.QSignalBlocker(self):
            self.model().clear()
            self.setModel(in_model)
            for col_idx, column_setting in enumerate(self.column_settings):
                self.model().setHorizontalHeaderItem(col_idx, QtGui.QStandardItem(column_setting.get('header', '')))
            self.view().setToolTip(self.view_tool_tip)
            self.view().resizeColumnsToContents()
            if self.show_clear_button and self.clear_button_icon:
                # must be applied here because clear_button_icon not parameter of __init__
                self.lineEdit().findChild(QtWidgets.QToolButton).setIcon(self.clear_button_icon)

            if self.resize_mode == 'resize_to_contents':
                calc_height = 0
                for rc in range(self.model().rowCount()):
                    calc_height += self.view().verticalHeader().sectionSize(rc)
                # if not self.view().horizontalScrollBar().isHidden():
                #     calc_height += self.view().horizontalScrollBar().height()
                #     # wird nicht angezeigt, aber ist trotzdem nicht hidden
                calc_height += self.view().horizontalHeader().height()
                calc_height += self.view().frameWidth() * 2
                calc_height += self.qsgr.height()
                self.calc_height = calc_height
                calc_width = 0
                for cc in range(self.model().columnCount()):
                    calc_width += self.view().columnWidth(cc)
                calc_width += self.view().frameWidth() * 2
                # add margins and paddings, estimated value via try
                # perhaps the sort-icons in header? On windows above the header, under linux beside the header
                calc_width += 15 * self.model().columnCount()
                # because of self.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
                if self.pop_up_height == self.window().windowHandle().screen().availableGeometry().height():
                    calc_width += 15
                self.calc_width = calc_width

            elif self.resize_mode == 'fix_size':
                self.pop_up_width = self.fix_width
                self.pop_up_height = self.fix_height











    def showPopup(self):
        """derived version, which opens popup
         positions it right below the LineEdit and resizes the width and height"""

        QtWidgets.QComboBox.showPopup(self)
        pop_up_frame = self.findChild(QtWidgets.QFrame)
        if not self.pop_up_width or self.pop_up_height:
            # first time call: calculate size
            if self.resize_mode == 'resize_to_contents':
                # enlarge to calculated necessary or LineEdit-width:
                self.pop_up_width = max(self.calc_width, self.width())
                # but not wider then current screen
                self.pop_up_width = min(self.pop_up_width, self.window().windowHandle().screen().availableGeometry().width())
                self.pop_up_height = min(self.calc_height, self.window().windowHandle().screen().availableGeometry().height())
            else:
                # resize to fixed size
                self.pop_up_width = self.fix_width
                self.pop_up_height = self.fix_height

        # later: resize to last size, evtl. user defined
        pop_up_frame.resize(self.pop_up_width, self.pop_up_height)

        left = self.mapToGlobal(QtCore.QPoint(0, 0)).x()
        top = self.mapToGlobal(QtCore.QPoint(0, 0)).y() + self.height()
        if top + pop_up_frame.height() > self.window().windowHandle().screen().availableGeometry().height():
            top = self.window().windowHandle().screen().availableGeometry().height() - pop_up_frame.height()
        pop_up_frame.move(left, top)


    def show_popup(self,event):
        """derived version, which opens popup
         positions it right below the LineEdit and resizes the width and height"""
        self.showPopup()


    class MyStandardItem(QtGui.QStandardItem):
        """derived QStandardItem used within QStandardItemModel:
        normal sort uses the text() (QtDisplayRole), which is not always usefull, especially for numerical values
        These QStandardItem uses Qt_Roles.CUSTOM_SORT"""
        # Rev. 2025-01-25
        def __init__(self, *args, **kwargs):
            """constructor
            :param args: parameter for super()-constructor
            :param kwargs: parameter for super()-constructor
            """
            # Rev. 2025-01-04
            super().__init__(*args, **kwargs)

        def __lt__(self, other):
            """derived operator for custom sort
            :param self: current QTableWidgetItem
            :param other: the compared QTableWidgetItem
            """
            # Rev. 2025-01-04
            try:
                lt = self.data(Qt_Roles.CUSTOM_SORT) < other.data(Qt_Roles.CUSTOM_SORT)
            except Exception as e:
                # "Leerstellen" im Modell: einer oder beide der sort_role-Werte nicht gesetzt
                # Fehlermeldung: '<' not supported between instances of 'NoneType' and 'NoneType'
                # True => Nullwerte werden aufsteigend am Anfang sortiert
                # False => Nullwerte werden aufsteigend am Ende sortiert
                # => hier notwendig, um erst die data_records und danach die recursive_childs darzustellen, was etwas verwirrend aussieht
                lt = False

            return lt
    def paintEvent(self, event):
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        painter = QtWidgets.QStylePainter(self)
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)
        if self.currentIndex() > -1:
            option_text_result = self.option_text_template

            # Zugriff auf die Modelldaten, die im dargestellten
            for col_idx, column_setting in enumerate(self.column_settings):
                item_idx = self.model().index(self.currentIndex(), col_idx)
                if column_setting.get('option_text_qexp'):
                    # Spezialwert via Ausdruck
                    option_value = self.model().itemData(item_idx).get(Qt_Roles.OPTION_TEXT)
                else:
                    # Default-Wert gem. aktueller Darstellung
                    option_value = self.model().itemData(item_idx).get(QtCore.Qt.DisplayRole)

                # avoid 'None' as displayValue
                option_text = ''
                if option_value is not None:
                    option_text = str(option_value)

                # f-string-artiges Suchen und Ersetzen {0} => column 0 {1} => column 1...
                option_text_result = option_text_result.replace(f"{{{col_idx}}}", option_text)

            if self.show_clear_button:
                # avoid disturbing blinking cursor...
                self.lineEdit().setText(option_text_result)
                # not necessary, lineEdit is readOnly
                # self.lineEdit().clearFocus()
            else:
                option.currentText = option_text_result

            painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, option)


    def select_by_value(self, cols_roles_flags: list, select_value: Any, block_signals: bool = True) -> QtCore.QModelIndex:
        """scans the recursive data-model for a specific value, selects the assigned rows and returns their row-indizes
        :param cols_roles_flags: list of lists [col_idx, role_idx, flags]
        :param select_value: the compare-value
        :param block_signals: do not trigger any indexChanged-signal
        :returns: found QModelIndex
        """
        # Rev. 2025-01-22
        if self.model():
            model = self.model()
            for col_role_flag in cols_roles_flags:
                col_idx = col_role_flag[0]
                role_idx = col_role_flag[1]
                flags = col_role_flag[2]
                # only one hit required
                matches = model.match(model.index(0, col_idx), role_idx, select_value, 1, flags)
                for index in matches:
                    self.blockSignals(block_signals)
                    self.setCurrentIndex(index.row())
                    self.blockSignals(False)
                    # select the first hit and return to sender
                    return index


class MyLayerSelectorQComboBox(MyQComboBox):
    """QtWidgets.QComboBox for select of Project-Layers with multiple and sortable columns, uses QtWidgets.QTableView
    only for select, not for edits"""
    # Rev. 2025-06-22

    def __init__(self, parent,column_pre_settings,option_text_template: str = '{0}', show_clear_button:bool = True, show_disabled:bool = False):
        """
        constructor
        :param parent: Qt-Hierarchy
        :param column_pre_settings: metadata for colums in QTableView
        :param option_text_template: Template for QLineEdit
        :param show_clear_button: show a button to clear current selected item
        :param show_disabled: True => disabled items are listed, False (default): disabled items are not listed making the list clearer
        """
        super().__init__(parent, column_pre_settings, option_text_template, show_clear_button)
        self.show_disabled = show_disabled
        self.pop_up_width = 500
        self.pop_up_height = 300

    def load_data(self, enable_criteria:dict = {}, disable_criteria:dict = {}) -> tuple:
        """
        :param enable_criteria: dictionary with positive validity-checks, checked first
        :param disable_criteria: dictionary with negative validity-checks, checked second
        each key of these dicts has a check-list:
            layer_type => enable/disable layer according to its type
                coarse structure
                https://api.qgis.org/api/classQgis.html#aa5105ead70f1fd9cd19258c08a9a513b
                enum class Qgis::LayerType
                    0 Vector layer
                    1 Raster layer
                    ...

            geometry_type => enable/disable layer according to its geometry type (automatically filters Vector-Layer)
                https://api.qgis.org/api/classQgis.html#a84964253bb44012b246c20790799c04d
                enum class Qgis::GeometryType : int
                Qgis.GeometryType.Point 0
                1 Line
                2 Polygon
                3 Unknown
                4 Null

            wkb_type => enable/disable layer according to its geometry-wkb-type (automatically filters Vector-Layer)
                fine structure
                https://api.qgis.org/api/classQgis.html#adf94495b88fbb3c5df092267ccc94509
                Qgis.WkbType.Unknown 0
                Qgis.WkbType.Point 1
                Qgis.WkbType.LineString 2 (nur einfache LineString, keine LineStringM/LineStringZ/MultiLineString...)
                Qgis.WkbType.Polygon 3

            data_provider => enable/disable layer according to its dataProvider().name()
                https://api.qgis.org/api/classQgsDataProvider.html
                wms
                ogr
                virtual

            crs => enable/disable layer according to its projection (list of QgsCoordinateReferenceSystem)

            layer_name => list of enabled/disabled layer-names
            layer_id => list of enabled/disabled layer-ids
            layer =>  list of enabled/disabled map-layers
        :return:
        """


        model = QtGui.QStandardItemModel(0, 4)
        # Leerzeile als erste, um bei setIndex(-1) nicht eine erste Zeile mit Werten darzustellen
        items = [self.MyStandardItem(), self.MyStandardItem(), self.MyStandardItem(), self.MyStandardItem()]
        model.appendRow(items)
        idx = 0
        # TOC order, may not be draw-order because of "Layer Order", but also geometry-less layers included
        # type: QgsLayerTreeLayer
        ltr_layers = qgis._core.QgsProject.instance().layerTreeRoot().findLayers()
        # TOC-order or Drawing-Order, but no geometry-less layer
        # layers = qgis._core.QgsProject.instance().layerTreeRoot().layerOrder()
        # unordered list, perhaps ordered by add-to-project-range?
        # layers = qgis._core.QgsProject.instance().mapLayers().values()

        # for cl in layers:
        for ltrl_layer in ltr_layers:
            if ltrl_layer.layer() and ltrl_layer.layer().isValid():
                cl = ltrl_layer.layer()
                name_item = self.MyStandardItem()
                name_item.setData(cl.name(), QtCore.Qt.DisplayRole)
                name_item.setData(cl.name(), Qt_Roles.CUSTOM_SORT)
                # Achtung: der Layer, der Name!
                name_item.setData(cl, Qt_Roles.RETURN_VALUE)

                geometry_item = self.MyStandardItem()
                if isinstance(cl, qgis._core.QgsVectorLayer):
                    display_value = qgis._core.QgsWkbTypes.displayString(cl.dataProvider().wkbType())
                else:
                    display_value = 'Raster'

                geometry_item.setData(display_value, QtCore.Qt.DisplayRole)
                geometry_item.setData(display_value, Qt_Roles.CUSTOM_SORT)

                provider_item = self.MyStandardItem()
                if isinstance(cl, qgis._core.QgsVectorLayer) and cl.dataProvider().name() != 'virtual':
                    display_value = f"{cl.dataProvider().name()} ({cl.dataProvider().storageType()})"
                else:
                    display_value = cl.dataProvider().name()

                provider_item.setData(cl.dataProvider().name(), QtCore.Qt.DisplayRole)
                provider_item.setData(display_value, Qt_Roles.CUSTOM_SORT)

                index_item = self.MyStandardItem(Qt_Roles.CUSTOM_SORT)
                index_item.setData(idx, QtCore.Qt.DisplayRole)
                index_item.setData(idx, Qt_Roles.CUSTOM_SORT)

                items = [name_item, geometry_item, provider_item, index_item]

                enabled = True
                if enable_criteria:
                    for key, value_list in enable_criteria.items():
                        if key == 'layer_type':
                            enabled &= cl.type() in value_list
                        elif key == 'geometry_type':
                            # AttributeError: 'QgsRasterLayer' object has no attribute 'geometryType'
                            enabled &= hasattr(cl, 'geometryType') and cl.geometryType() in value_list
                        elif key == 'wkb_type':
                            # AttributeError: 'QgsRasterLayer' object has no attribute 'geometryType'
                            enabled &= hasattr(cl, 'wkbType') and cl.wkbType() in value_list
                        elif key == 'layer_name':
                            enabled &= cl.name() in value_list
                        elif key == 'layer_id':
                            enabled &= cl.id() in value_list
                        elif key == 'layer':
                            enabled &= cl in value_list
                        elif key == 'data_provider':
                            enabled &= hasattr(cl, 'dataProvider') and cl.dataProvider().name() in value_list
                        elif key == 'crs':
                            enabled &= hasattr(cl, 'crs') and cl.crs() in value_list
                        else:
                            raise NotImplementedError(f"enable_criteria '{key}' not in field_type/field_origin/field_name/field_idx")

                if disable_criteria:
                    for key,value_list in disable_criteria.items():
                        if key == 'layer_type':
                            enabled &= cl.type() in value_list
                        elif key == 'geometry_type':
                            enabled &= not(hasattr(cl, 'geometryType') and cl.geometryType() in value_list)
                        elif key == 'wkb_type':
                            # AttributeError: 'QgsRasterLayer' object has no attribute 'geometryType'
                            enabled &= not(hasattr(cl, 'wkbType') and cl.wkbType() in value_list)
                        elif key == 'layer_name':
                            enabled &= cl.name() not in value_list
                        elif key == 'layer_id':
                            enabled &= cl.id() not in value_list
                        elif key == 'layer':
                            enabled &= cl not in value_list
                        elif key == 'data_provider':
                            enabled &= not(hasattr(cl, 'dataProvider') and cl.dataProvider().name() in value_list)
                        elif key == 'crs':
                            enabled &= not(hasattr(cl, 'crs') and cl.crs() in value_list)
                        else:
                            raise NotImplementedError(f"disable_criteria '{key}' not in field_type/field_origin/field_name/field_idx")




                for col_idx, item in enumerate(items):
                    item.setEnabled(enabled)

                    column_setting = self.column_settings[col_idx]
                    icon = column_setting.get('icon', None)
                    if icon:
                        item.setData(icon, QtCore.Qt.DecorationRole)

                    alignment = column_setting.get('alignment', None)
                    if alignment:
                        item.setTextAlignment(alignment)

                    font = column_setting.get('font', None)
                    if font:
                        item.setFont(font)

                    tool_tip = column_setting.get('tool_tip', None)
                    if tool_tip:
                        item.setData(tool_tip, QtCore.Qt.ToolTipRole)

                if enabled or self.show_disabled:
                    model.appendRow(items)

            idx += 1

        self.set_model(model)