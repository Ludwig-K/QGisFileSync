#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin FileSync:
* Qt-Dialog

********************************************************************

* Date                 : 2025-04-11
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

********************************************************************
"""
import qgis
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFontDatabase, QTextOption

from FileSync.qt import MyQtWidgets
from FileSync.tools import MyTools


class FileSyncDialog(QtWidgets.QDockWidget):
    """Dialogue for QGis-Plugin FileSync
    note:
        QtWidgets.QDockWidget -> dockable Window
        requires self.iface.addDockWidget(...) to be dockable within the MainWindow
    """

    def __init__(self, iface: qgis.gui.QgisInterface, parent=None):
        """Constructor
        :param iface:
        :param parent: optional Qt-Parent-Element for Hierarchy
        """

        QtWidgets.QDockWidget.__init__(self, parent)

        self.iface = iface
        self.setWindowTitle('FileSync Plugin')

        # to avoid ShutDown-Warning
        # Warning: QMainWindow::saveState(): 'objectName' not set for QDockWidget 0x55bc0824c790
        self.setObjectName("FileSync-Dialog")

        main_wdg = QtWidgets.QWidget()
        main_wdg.setLayout(QtWidgets.QVBoxLayout())

        # central widget with mutiple tabs
        self.tbw_central = QtWidgets.QTabWidget(self)
        self.tbw_central.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)

        # Start pre_scan_tab
        if True:
            pre_scan_tab = QtWidgets.QWidget(self)
            pre_scan_tab.setLayout(QtWidgets.QGridLayout())

            row = 0

            pre_scan_tab.layout().addWidget(QtWidgets.QLabel('Scan-Directory:', self), row, 0)

            self.qle_pre_scan_dir = QtWidgets.QLineEdit()
            self.qle_pre_scan_dir.setReadOnly(True)
            pre_scan_tab.layout().addWidget(self.qle_pre_scan_dir, row, 1)

            self.qpb_select_pre_scan_dir = QtWidgets.QPushButton('...', self)
            pre_scan_tab.layout().addWidget(self.qpb_select_pre_scan_dir, row, 2)

            row += 1
            pre_scan_tab.layout().addWidget(QtWidgets.QLabel('Include Sub-Directories:', self), row, 0)
            self.qcb_pre_scan_sub_dirs = QtWidgets.QCheckBox()
            pre_scan_tab.layout().addWidget(self.qcb_pre_scan_sub_dirs, row, 1)

            row += 1
            pre_scan_tab.layout().addWidget(QtWidgets.QLabel('File-Extension(s):', self), row, 0)

            self.qle_pre_scan_patterns = QtWidgets.QLineEdit()
            self.qle_pre_scan_patterns.setToolTip('comma/semicolon/space-separated list of patterns, used case-insensitive')
            pre_scan_tab.layout().addWidget(self.qle_pre_scan_patterns, row, 1)

            self.qcb_select_pre_scan_patterns = QtWidgets.QComboBox(self)
            self.qcb_select_pre_scan_patterns.setMaximumWidth(100)
            self.qcb_select_pre_scan_patterns.addItem(None)
            # https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Image_types
            pre_scan_suffices = [
                "*.*",
                "*.jpg *.jpeg",
                "*.pdf",
                "*.doc *.docx *.xls *.xlsx *.ppt *.pptx *.odt *.ods *.odp *.odg",
                "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.gif"
            ]
            self.qcb_select_pre_scan_patterns.addItems(pre_scan_suffices)

            pre_scan_tab.layout().addWidget(self.qcb_select_pre_scan_patterns, row, 2)

            row += 1
            pre_scan_tab.layout().addWidget(QtWidgets.QLabel('Out-Projection:', self), row, 0)

            self.qle_pre_scan_epsg = QtWidgets.QLineEdit()
            self.qle_pre_scan_epsg.setToolTip('specifiy projection of generated temporary layer, via exif georeferenced jpeg (WGS 84) will be transformed')
            self.qle_pre_scan_epsg.setReadOnly(True)

            pre_scan_tab.layout().addWidget(self.qle_pre_scan_epsg, row, 1)

            self.qpb_select_pre_scan_crs = QtWidgets.QPushButton('...', self)
            pre_scan_tab.layout().addWidget(self.qpb_select_pre_scan_crs, row, 2)

            row += 1

            pre_scan_export_fields_grb = MyQtWidgets.QGroupBoxExpandable('Extract File-Metas:', False, self)
            pre_scan_export_fields_grb.setLayout(QtWidgets.QHBoxLayout())

            self.qsa_pre_scan = QtWidgets.QScrollArea(self)
            self.qsa_pre_scan.setWidgetResizable(True)
            self.qsa_pre_scan.setMinimumHeight(400)
            pre_scan_export_fields_grb.layout().addWidget(self.qsa_pre_scan)

            pre_scan_tab.layout().addWidget(pre_scan_export_fields_grb, row, 0, 1, 3)

            row += 1
            self.qpb_start_pre_scan = QtWidgets.QPushButton('Start PreScan...', self)
            pre_scan_tab.layout().addWidget(self.qpb_start_pre_scan, row, 0, 1, 3)

            row += 1

            # PreScan can take a long time where QGis seems to freeze, so show current progress for impatient users
            self.sub_wdg_pre_scan_progress = QtWidgets.QWidget()
            self.sub_wdg_pre_scan_progress.setLayout(QtWidgets.QHBoxLayout())
            self.sub_wdg_pre_scan_progress.setVisible(False)

            self.qlbl_pre_scan_progress = QtWidgets.QLabel(self)
            self.qlbl_pre_scan_progress.setMinimumWidth(150)
            self.sub_wdg_pre_scan_progress.layout().addWidget(self.qlbl_pre_scan_progress)

            self.qprb_pre_scan = QtWidgets.QProgressBar(self)
            self.sub_wdg_pre_scan_progress.layout().addWidget(self.qprb_pre_scan)

            pre_scan_tab.layout().addWidget(self.sub_wdg_pre_scan_progress, row, 0, 1, 3)

            row += 1
            pre_scan_tab.layout().setRowStretch(row, 1)

            self.tbw_central.addTab(pre_scan_tab, 'PreScan')

        # End pre_scan_tab ######################################################################################
        if True:
            sync_tab = QtWidgets.QWidget(self)
            sync_tab.setLayout(QtWidgets.QVBoxLayout())

            self.grid_container_wdg = QtWidgets.QWidget()
            self.grid_container_wdg.setLayout(QtWidgets.QGridLayout())

            sub_row = 0
            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('<b>Source:</b>', self), sub_row, 1, 1, 2)
            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('<b>Target:</b>', self), sub_row, 3, 1, 2)

            sub_row += 1
            sub_wdg = QtWidgets.QWidget()
            sub_wdg.setLayout(QtWidgets.QHBoxLayout())
            sub_wdg.layout().setContentsMargins(0, 5, 5, 5)
            qtb = MyQtWidgets.QtbToggleGridRows(self.grid_container_wdg, sub_row + 1, sub_row + 2)
            sub_wdg.layout().addWidget(qtb)

            qlbl = QtWidgets.QLabel("Sync-Layers")
            sub_wdg.layout().addWidget(qlbl)
            self.grid_container_wdg.layout().addWidget(sub_wdg, sub_row, 0, 1, 10, QtCore.Qt.AlignLeft)

            sub_row += 1

            column_pre_settings = [{'header': 'Layer'}, {'header': 'Geometry'}, {'header': 'Provider'}, {'header': 'idx'}]
            self.qcbn_sync_source_layer = MyQtWidgets.MyLayerSelectorQComboBox(self, column_pre_settings, show_disabled=True)
            self.qcbn_sync_source_layer.setToolTip('Select Source-Layer')
            self.grid_container_wdg.layout().addWidget(self.qcbn_sync_source_layer, sub_row, 1)

            self.qpb_open_sync_source_table = QtWidgets.QPushButton(self)
            self.qpb_open_sync_source_table.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionOpenTable.svg'))
            self.qpb_open_sync_source_table.setToolTip('Open feature-table')
            self.qpb_open_sync_source_table.setMaximumWidth(50)
            self.grid_container_wdg.layout().addWidget(self.qpb_open_sync_source_table, sub_row, 2)

            column_pre_settings = [{'header': 'Layer'}, {'header': 'Geometry'}, {'header': 'Provider'}, {'header': 'idx'}]
            self.qcbn_sync_target_layer = MyQtWidgets.MyLayerSelectorQComboBox(self, column_pre_settings, show_disabled=True)
            self.qcbn_sync_target_layer.setToolTip('Select Target-Layer')
            self.grid_container_wdg.layout().addWidget(self.qcbn_sync_target_layer, sub_row, 3)

            self.qpb_open_sync_target_table = QtWidgets.QPushButton(self)
            self.qpb_open_sync_target_table.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionOpenTable.svg'))
            self.qpb_open_sync_target_table.setToolTip('Open feature-table')
            self.qpb_open_sync_target_table.setMaximumWidth(50)
            self.grid_container_wdg.layout().addWidget(self.qpb_open_sync_target_table, sub_row, 4)

            self.qpb_refresh_sync_layers = QtWidgets.QPushButton(self)
            self.qpb_refresh_sync_layers.setToolTip("Refresh listed layers and fields")
            self.qpb_refresh_sync_layers.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionRefresh.svg'))
            self.qpb_refresh_sync_layers.setMaximumWidth(50)
            self.grid_container_wdg.layout().addWidget(self.qpb_refresh_sync_layers, sub_row, 0,1,1,QtCore.Qt.AlignCenter)

            sub_row += 1

            sub_wdg = QtWidgets.QWidget()
            sub_wdg.setLayout(QtWidgets.QHBoxLayout())
            sub_wdg.layout().setContentsMargins(0, 5, 5, 5)
            qtb = MyQtWidgets.QtbToggleGridRows(self.grid_container_wdg, sub_row + 1, sub_row + 9)
            sub_wdg.layout().addWidget(qtb)

            qlbl = QtWidgets.QLabel("Sync-Files")
            sub_wdg.layout().addWidget(qlbl)
            self.grid_container_wdg.layout().addWidget(sub_wdg, sub_row, 0, 1, 10, QtCore.Qt.AlignLeft)

            sub_row += 1
            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('Absolute-Path-Field:'), sub_row, 0)
            self.qcb_sync_source_abs_path_field = QtWidgets.QComboBox(self)
            self.qcb_sync_source_abs_path_field.setToolTip('Field for absolute-path in Source-Layer, mandatory for File-Handling')
            self.grid_container_wdg.layout().addWidget(self.qcb_sync_source_abs_path_field, sub_row, 1, 1, 2)

            self.qcb_sync_target_abs_path_field = QtWidgets.QComboBox(self)
            self.qcb_sync_target_abs_path_field.setToolTip('Field for absolute-path in Target-Layer, which can be different to original path dependent on File-Handling')
            self.grid_container_wdg.layout().addWidget(self.qcb_sync_target_abs_path_field, sub_row, 3, 1, 2)


            sub_row += 1

            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('File-Mode:'), sub_row, 0,2,1)

            self.qrb_sync_mode_keep = QtWidgets.QRadioButton('Keep')
            self.qrb_sync_mode_keep.setToolTip('Keep files in place specified by absolute-path-field')
            self.grid_container_wdg.layout().addWidget(self.qrb_sync_mode_keep, sub_row, 3)

            sub_row += 1

            self.qrb_sync_mode_copy = QtWidgets.QRadioButton('Copy')
            self.qrb_sync_mode_copy.setToolTip('Copy files to specified target-directory/sub-directory')

            self.grid_container_wdg.layout().addWidget(self.qrb_sync_mode_copy, sub_row, 3)

            self.qbgrp = QtWidgets.QButtonGroup()
            self.qbgrp.setExclusive(True)
            self.qbgrp.addButton(self.qrb_sync_mode_keep)
            self.qbgrp.addButton(self.qrb_sync_mode_copy)

            sub_row += 1

            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('Target-Directory:'), sub_row, 0)
            self.qle_sync_target_dir = QtWidgets.QLineEdit(self)
            self.qle_sync_target_dir.setReadOnly(True)
            self.grid_container_wdg.layout().addWidget(self.qle_sync_target_dir, sub_row, 3)

            self.qpb_select_sync_target_dir = QtWidgets.QPushButton('...', self)
            self.qpb_select_sync_target_dir.setMaximumWidth(50)
            self.grid_container_wdg.layout().addWidget(self.qpb_select_sync_target_dir, sub_row, 4)

            sub_row += 1

            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('Sub-Directory from Field\n(optional):'), sub_row, 0)

            self.qcb_sync_source_rel_path_field = QtWidgets.QComboBox(self)
            self.qcb_sync_source_rel_path_field.setToolTip('for File-Modes Copy: optional field in Source-Layer containing a relative path, which will be preserved in target-directory')
            self.grid_container_wdg.layout().addWidget(self.qcb_sync_source_rel_path_field, sub_row, 1,1,2)

            sub_row += 1
            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('Existing-File-Mode:'), sub_row, 0)
            self.qcb_sync_existing_file_mode = QtWidgets.QComboBox(self.grid_container_wdg)

            self.qcb_sync_existing_file_mode.setSizePolicy(QtWidgets.QSizePolicy.Ignored, self.qcb_sync_existing_file_mode.sizePolicy().verticalPolicy())
            self.qcb_sync_existing_file_mode.setToolTip("For File-Mode 'Copy': how to handle existing files with same path")
            self.qcb_sync_existing_file_mode.addItem(None)

            existing_file_modes = {
                "replace": 'replace file',
                "rename": 'rename file (keep old file)',
                "skip": 'skip (keep old file)',
            }
            for existing_file_mode, existing_file_mode_str in existing_file_modes.items():
                self.qcb_sync_existing_file_mode.addItem(existing_file_mode_str, existing_file_mode)

            self.grid_container_wdg.layout().addWidget(self.qcb_sync_existing_file_mode, sub_row, 3,1,2)

            sub_row += 1
            self.grid_container_wdg.layout().addWidget(QtWidgets.QLabel('Existing-Feature-Mode:'), sub_row, 0)
            self.qcb_sync_existing_feature_mode = QtWidgets.QComboBox(self.grid_container_wdg)

            self.qcb_sync_existing_feature_mode.setSizePolicy(QtWidgets.QSizePolicy.Ignored, self.qcb_sync_existing_feature_mode.sizePolicy().verticalPolicy())
            self.qcb_sync_existing_feature_mode.setToolTip("how to handle existing features with same absolute path")
            self.qcb_sync_existing_feature_mode.addItem(None)

            existing_feature_modes = {
                "update_overwrite": 'update, overwrite existing values',
                "update_preserve": 'update, preserve existing values',
                "insert": 'insert duplicate',
                "replace": 'replace',
                "skip": 'skip',
            }
            for existing_feature_mode, existing_feature_mode_str in existing_feature_modes.items():
                self.qcb_sync_existing_feature_mode.addItem(existing_feature_mode_str, existing_feature_mode)

            self.grid_container_wdg.layout().addWidget(self.qcb_sync_existing_feature_mode, sub_row, 3,1,2)

            sub_row += 1
            self.qcb_sync_update_geometries = QtWidgets.QCheckBox("update geometries")
            self.qcb_sync_update_geometries.setToolTip("for existing-feature-updates: update feature-geometry or keep existing")
            self.grid_container_wdg.layout().addWidget(self.qcb_sync_update_geometries, sub_row, 3, 1, 2)





            sub_row += 1
            sub_wdg = QtWidgets.QWidget()
            sub_wdg.setLayout(QtWidgets.QHBoxLayout())
            sub_wdg.layout().setContentsMargins(0, 5, 5, 5)
            qtb = MyQtWidgets.QtbToggleGridRows(self.grid_container_wdg, sub_row + 1, sub_row + 99)
            sub_wdg.layout().addWidget(qtb)

            qlbl = QtWidgets.QLabel("Sync-Fields")
            sub_wdg.layout().addWidget(qlbl)
            self.grid_container_wdg.layout().addWidget(sub_wdg, sub_row, 0, 1, 5, QtCore.Qt.AlignLeft)

            sub_row += 1
            self.qlw_sync_source_layer_fields = QtWidgets.QListWidget()

            self.qlw_sync_source_layer_fields.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.grid_container_wdg.layout().addWidget(self.qlw_sync_source_layer_fields, sub_row, 1, 1, 2)

            self.qlw_sync_target_layer_fields = QtWidgets.QListWidget()
            self.qlw_sync_target_layer_fields.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.grid_container_wdg.layout().addWidget(self.qlw_sync_target_layer_fields, sub_row, 3,1,2)

            sub_row += 1
            self.qpb_add_sync_mapping = QtWidgets.QPushButton("▼ Add ▼", self)
            self.qpb_add_sync_mapping.setToolTip("add selected fields as mapping")

            self.grid_container_wdg.layout().addWidget(self.qpb_add_sync_mapping, sub_row, 1, 1,4)

            sub_row += 1
            # Note: Attempts to solve this inside self.grid_container_wdg by adding/removing cells, but this seems to be quite complicated
            #https://stackoverflow.com/questions/5395266/removing-widgets-from-qgridlayout
            self.qtw_sync_mappings = QtWidgets.QTableWidget()
            self.qtw_sync_mappings.setColumnCount(4)
            self.qtw_sync_mappings.setHorizontalHeaderLabels(('', '', '',''))
            self.qtw_sync_mappings.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
            # columns are dynamically resized to fit into QGridLayout, see dlg_resize_sync_cols
            self.qtw_sync_mappings.setColumnWidth(0, 170)
            self.qtw_sync_mappings.setColumnWidth(1, 15)
            self.qtw_sync_mappings.setColumnWidth(2, 170)
            self.qtw_sync_mappings.setColumnWidth(3, 30)
            self.qtw_sync_mappings.horizontalHeader().setStretchLastSection(True)
            self.grid_container_wdg.layout().addWidget(self.qtw_sync_mappings, sub_row, 1, 1, 4)

            sub_row += 1
            self.qpb_clear_sync_mappings = QtWidgets.QPushButton("✖ Clear ✖", self)
            self.qpb_clear_sync_mappings.setToolTip("remove all mappings")
            self.grid_container_wdg.layout().addWidget(self.qpb_clear_sync_mappings, sub_row, 1, 1, 4)

            sync_tab.layout().addWidget(self.grid_container_wdg)

            # PreScan can take a long time where QGis seems to freeze, so show current progress for impatient users
            self.sub_wdg_file_sync_progress = QtWidgets.QWidget()
            self.sub_wdg_file_sync_progress.setLayout(QtWidgets.QHBoxLayout())
            self.sub_wdg_file_sync_progress.setVisible(False)

            self.qlbl_file_sync_progress = QtWidgets.QLabel(self)
            self.qlbl_file_sync_progress.setMinimumWidth(150)
            self.sub_wdg_file_sync_progress.layout().addWidget(self.qlbl_file_sync_progress)

            self.qprb_file_sync = QtWidgets.QProgressBar(self)
            self.sub_wdg_file_sync_progress.layout().addWidget(self.qprb_file_sync)

            sync_tab.layout().addWidget(self.sub_wdg_file_sync_progress)

            self.qpb_start_sync = QtWidgets.QPushButton("Start Synchronize...", self)
            self.qpb_start_sync.setToolTip("Synchronize temporary Pre-Scan-Result with permanent Target-Layer")
            sync_tab.layout().addWidget(self.qpb_start_sync)

            # add a stretch below to push the contents to the top and not spread it vertically
            sync_tab.layout().addStretch(1)

            self.tbw_central.addTab(sync_tab, 'Sync')

        if True:
            post_scan_tab = QtWidgets.QWidget(self)
            post_scan_tab.setLayout(QtWidgets.QGridLayout())

            row = 0

            post_scan_tab.layout().addWidget(QtWidgets.QLabel('PostScan-Layer:'), row, 0)

            column_pre_settings = [{'header': 'Layer'}, {'header': 'Geometry'}, {'header': 'Provider'}, {'header': 'idx'}]
            self.qcbn_post_scan_layer = MyQtWidgets.MyLayerSelectorQComboBox(self, column_pre_settings, show_disabled=False)
            self.qcbn_post_scan_layer.setToolTip('Select Target-Layer')
            post_scan_tab.layout().addWidget(self.qcbn_post_scan_layer, row, 1)

            self.qpb_open_post_scan_layer = QtWidgets.QPushButton(self)
            self.qpb_open_post_scan_layer.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionOpenTable.svg'))
            self.qpb_open_post_scan_layer.setToolTip('Open feature-table')
            self.qpb_open_post_scan_layer.setMaximumWidth(50)
            post_scan_tab.layout().addWidget(self.qpb_open_post_scan_layer, row, 2)

            self.qpb_refresh_post_scan_layer = QtWidgets.QPushButton(self)
            self.qpb_refresh_post_scan_layer.setToolTip("Refresh listed layers and fields")
            self.qpb_refresh_post_scan_layer.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionRefresh.svg'))
            self.qpb_refresh_post_scan_layer.setMaximumWidth(50)
            post_scan_tab.layout().addWidget(self.qpb_refresh_post_scan_layer, row, 3)

            row += 1
            post_scan_tab.layout().addWidget(QtWidgets.QLabel('Absolute-Path-Field:'), row, 0)
            self.qcb_post_scan_abs_path_field = QtWidgets.QComboBox(self)
            self.qcb_post_scan_abs_path_field.setToolTip('Field for absolute-path in Post-Scan-Layer')
            post_scan_tab.layout().addWidget(self.qcb_post_scan_abs_path_field, row, 1, 1, 3)

            row += 1
            self.qcb_post_scan_preserve_existing = QtWidgets.QCheckBox("preserve existing data")
            self.qcb_post_scan_preserve_existing.setToolTip("preserve existing/update missing: update field-values/geometries with queried file-metas only if field-value rsp. geometry is empty")
            post_scan_tab.layout().addWidget(self.qcb_post_scan_preserve_existing, row, 1, 1, 3)

            row += 1
            self.qcb_post_scan_update_geometry_from_exif = QtWidgets.QCheckBox("update geometries")
            self.qcb_post_scan_update_geometry_from_exif.setToolTip("only for jpeg-files with exif-metas containing gps-latitude/longitude/altitude")
            post_scan_tab.layout().addWidget(self.qcb_post_scan_update_geometry_from_exif, row, 1, 1, 3)

            row += 1
            post_scan_export_fields_grb = MyQtWidgets.QGroupBoxExpandable('Extract File-Metas:', False, self)
            post_scan_export_fields_grb.setLayout(QtWidgets.QHBoxLayout())

            self.qsa_post_scan = QtWidgets.QScrollArea(self)
            self.qsa_post_scan.setWidgetResizable(True)
            self.qsa_post_scan.setMinimumHeight(400)
            post_scan_export_fields_grb.layout().addWidget(self.qsa_post_scan)

            post_scan_tab.layout().addWidget(post_scan_export_fields_grb, row, 0, 1, 4)

            row += 1

            self.qpb_start_post_scan = QtWidgets.QPushButton('Start PostScan...', self)
            self.qpb_start_post_scan.setToolTip('Extract file-meta-data for registered files und update features in PostScan-Layer')
            post_scan_tab.layout().addWidget(self.qpb_start_post_scan, row, 0, 1, 4)

            row += 1
            # PreScan can take a long time where QGis seems to freeze, so show current progress for impatient users
            self.sub_wdg_post_scan_progress = QtWidgets.QWidget()
            self.sub_wdg_post_scan_progress.setLayout(QtWidgets.QHBoxLayout())
            self.sub_wdg_post_scan_progress.setVisible(False)

            self.qlbl_post_scan_progress = QtWidgets.QLabel(self)
            self.qlbl_post_scan_progress.setMinimumWidth(150)
            self.sub_wdg_post_scan_progress.layout().addWidget(self.qlbl_post_scan_progress)

            self.qprb_post_scan = QtWidgets.QProgressBar(self)
            self.sub_wdg_post_scan_progress.layout().addWidget(self.qprb_post_scan)

            post_scan_tab.layout().addWidget(self.sub_wdg_post_scan_progress, row, 0, 1, 4)

            row += 1
            post_scan_tab.layout().setRowStretch(row, 1)

            self.tbw_central.addTab(post_scan_tab, 'PostScan')

        if True:
            # Log-Area
            log_tab = QtWidgets.QWidget(self)
            log_tab.setLayout(QtWidgets.QVBoxLayout())

            self.qte_log = QtWidgets.QTextEdit()
            self.qte_log.setAcceptRichText(True)
            self.qte_log.setReadOnly(True)

            fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            fixed_font.setPixelSize(11)

            self.qte_log.setFont(fixed_font)
            self.qte_log.setWordWrapMode(QTextOption.NoWrap)

            log_tab.layout().addWidget(self.qte_log)

            sub_wdg = QtWidgets.QWidget(self)
            sub_wdg.setLayout(QtWidgets.QHBoxLayout())

            self.qpb_skip_log_back = QtWidgets.QPushButton('Back')
            self.qpb_skip_log_back.setToolTip("Show previous in Log-History")
            self.qpb_skip_log_back.setCursor(QtCore.Qt.PointingHandCursor)
            self.qpb_skip_log_back.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionArrowLeft.svg'))
            sub_wdg.layout().addWidget(self.qpb_skip_log_back)

            self.qpb_skip_log_for = QtWidgets.QPushButton('For')
            self.qpb_skip_log_for.setToolTip("Show next in Log-History")
            self.qpb_skip_log_for.setCursor(QtCore.Qt.PointingHandCursor)
            self.qpb_skip_log_for.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionArrowRight.svg'))
            sub_wdg.layout().addWidget(self.qpb_skip_log_for)

            self.qpb_clear_log = QtWidgets.QPushButton('Clear')
            self.qpb_clear_log.setToolTip("Clear Log-History")
            self.qpb_clear_log.setCursor(QtCore.Qt.PointingHandCursor)
            self.qpb_clear_log.setIcon(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionDeleteSelectedFeatures.svg'))
            sub_wdg.layout().addWidget(self.qpb_clear_log)

            log_tab.layout().addWidget(sub_wdg)

            #

            self.tbw_central.addTab(log_tab, 'Log')

        self.tbw_central.setTabToolTip(0, 'Pre-Scan directory to temporary Point-Layer')
        self.tbw_central.setTabToolTip(1, 'Synchronize Pre-Scan-Layer with permanent Layer')
        self.tbw_central.setTabToolTip(2, 'Log-Messages')

        main_wdg.layout().addWidget(self.tbw_central)

        self.setWidget(main_wdg)
