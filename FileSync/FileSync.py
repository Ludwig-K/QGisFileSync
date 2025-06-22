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
import os, qgis, webbrowser
import shutil
import typing
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from pathlib import Path
from configparser import ConfigParser
from PIL import Image, IptcImagePlugin
from PIL.ExifTags import TAGS, GPSTAGS

from FileSync.tools import MyTools
from FileSync.tools.MyTools import debug_log, re_open_attribute_tables
from FileSync.settings.constants import Qt_Roles
from FileSync.dialogs.FileSyncDialog import FileSyncDialog

from FileSync.tools.MapTools import FeatureDigitizeMapTool


class FileMetaExtractor():
    """Tool to extract metadata from files"""

    # Rev. 2025-06-11
    def __init__(self, hash_alg: str = 'sha1'):
        """
        constructor
        :param hash_alg: hash-algorithm to calculate hash-value for a file, default sha1, unique fingerprint, usable for duplicate-check
        """
        # Rev. 2025-06-11

        # central configuration part: which metadata can be extracted from file?
        # key: meta_name, value: dictionary meta-metas
        self.extractable_file_metas = {
            'abs_path': {
                # type of the field
                'field_type': QtCore.QMetaType.QString,
                # is the field mandatory
                'mandatory': True,
                # default-field-name if used to create a new layer, mostly same value as meta_name
                'default_field_name': 'abs_path',
                # description used as user-info
                'description': 'absolute path to file'
            },
            'file_hash': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'file_hash',
                'description': 'unique hash (fingerprint, usable to identify duplicates independend from filename or file-meta-data)',
                'url': 'https://de.wikipedia.org/wiki/Secure_Hash_Algorithm'
            },
            'rel_path': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'rel_path',
                'description': 'Path relative to a root directory to be specified (without file-name)'
            },
            'file_name': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'file_name',
                'description': 'file-name'
            },
            'extension': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'extension',
                'description': 'file-extension (lowercase without dot)'
            },
            'exif_metas': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'exif_metas',
                'description': 'EXIF-metadata (Exchangeable image file format\nonly for images, f. e. camera, time, GPS)',
                'url': 'https://en.wikipedia.org/wiki/Exif'
            },
            'iptc_metas': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'iptc_metas',
                'description': 'IPTC-metadata (if available)',
                'url': 'https://en.wikipedia.org/wiki/IPTC_Information_Interchange_Model'
            },
            'xmp_metas': {
                'field_type': QtCore.QMetaType.QString,
                'mandatory': False,
                'default_field_name': 'xmp_metas',
                'description': 'XMP-metadata (Extensible Metadata, if available)',
                'url': 'https://en.wikipedia.org/wiki/Extensible_Metadata_Platform'
            },

            'file_size': {
                'field_type': QtCore.QMetaType.Int,
                'mandatory': False,
                'default_field_name': 'file_size',
                'description': 'total size in bytes',
            },

            'image_width': {
                'field_type': QtCore.QMetaType.Int,
                'mandatory': False,
                'default_field_name': 'image_width',
                'description': 'for images: width in pixel',
            },
            'image_height': {
                'field_type': QtCore.QMetaType.Int,
                'mandatory': False,
                'default_field_name': 'image_height',
                'description': 'for images: height in pixel',
            },
            'gps_latitude': {
                'field_type': QtCore.QMetaType.Double,
                'mandatory': False,
                'default_field_name': 'gps_latitude',
                'description': 'for images with exif-header containing GPS-metas:\nlatitude of recording point',
            },
            'gps_longitude': {
                'field_type': QtCore.QMetaType.Double,
                'mandatory': False,
                'default_field_name': 'gps_longitude',
                'description': 'for images with exif-header containing GPS-metas:\nlongitude of recording point',

            },
            'gps_altitude': {
                'field_type': QtCore.QMetaType.Double,
                'mandatory': False,
                'default_field_name': 'gps_altitude',
                'description': 'for images with exif-header containing GPS-metas:\naltitude of recording point',
            },
            'gps_img_direction': {
                'field_type': QtCore.QMetaType.Double,
                'mandatory': False,
                'default_field_name': 'gps_img_direction',
                'description': 'for images with exif-header containing GPS-metas:\nrecording-direction counter-clockwise against north',
            },
            'm_time': {
                'field_type': QtCore.QMetaType.QDateTime,
                'mandatory': False,
                'default_field_name': 'm_time',
                'description': 'Modification time: time when the content of the file most recently changed\n(even if file was identically saved)',
                'url': 'https://en.wikipedia.org/wiki/MAC_times'
            },
            'c_time': {
                'field_type': QtCore.QMetaType.QDateTime,
                'mandatory': False,
                'default_field_name': 'c_time',
                'description': 'Windows → creation time vs. Unix → change of metadata (owner, permission)',
                'url': 'https://en.wikipedia.org/wiki/MAC_times'
            },
            'a_time': {
                'field_type': QtCore.QMetaType.QDateTime,
                'mandatory': False,
                'default_field_name': 'a_time',
                'description': 'Access time: time when the file was most recently opened for reading\n(Note: in Windows file access time updating is disabled by default)',
                'url': 'https://en.wikipedia.org/wiki/MAC_times'
            },
            'date_time_original': {
                'field_type': QtCore.QMetaType.QDateTime,
                'mandatory': False,
                'description': 'for images with exif-header: recording-time',
                'default_field_name': 'date_time_original',
            },

        }

        # hash-algorithm to calculate hash-value for a file
        self.hash_alg = hash_alg

        # widget for pre-scan-usage (create new layer), Table (QGridLayout), one row for each meta, QLineEdits for user-defined field-name
        self.pre_scan_widget = None
        # widget for special meta rel_path inside pre_scan_widget, root-directory for the relative-path-calculation
        self.qle_pre_scan_rel_root_dir = None

        # widget for post-scan-usage (update values in existing layer), Table (QGridLayout), one row for each meta, QQomboBox to select meta-target-field from target-layer
        self.post_scan_widget = None
        # widget for special meta rel_path inside post_scan_widget, root-directory for the relative-path-calculation
        self.qle_post_scan_rel_root_dir = None

    def extract_file_metas(self, posix_path: Path, feature: qgis._core.QgsFeature, field_list: dict, pre_scan_rel_root_dir: str = None, preserve_existing: bool = False, extract_gps_geom: bool = False, tr_wgs_2_vl: qgis._core.QgsCoordinateTransform = None) -> tuple:
        """
        extract metadata from file to feature
        :param posix_path: absolute path to the extracted file
        :param feature: update or insert
        :param field_list: dict key: meta-name value: field-name
        :param pre_scan_rel_root_dir: additional for the rel_path-meta
        :param preserve_existing: pre-check existing data/geometry in feature and update only if no existing values found
        :param extract_gps_geom: optional set/update feature-geometry from exif-gps-coords (only jpegs with exif-header containing gps-coords)
        :param tr_wgs_2_vl: transformation from wgs-gps-coords to layer-crs if extract_gps_geom is True
        :return: tuple(extract_ok,feature_altered,extract_log)
        """
        # Rev. 2025-06-11
        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3

        extract_ok = True
        feature_altered = False
        extract_log = []

        if posix_path.is_file():
            # extract_log.append(f"{tab}extract_file_metas '{posix_path.as_posix()}'")

            # statistical meta-data (file-size, mTime, cTime, aTime)
            # os.stat_result(st_mode=33188, st_ino=3579220, st_dev=66306, st_nlink=1, st_uid=1000, st_gid=1000, st_size=5249572, st_atime=1749586047, st_mtime=1719916604, st_ctime=1744744426)
            stat_metas = posix_path.stat()

            # extract special metas for image-files and jpeg-exif
            img = None
            exif_dict = {}
            geo_exif_dict = {}
            lat = lon = alt = direction = None
            try:
                # try to open file as image:
                with Image.open(str(posix_path)) as img:
                    extract_log.append(f"{tab}{tab}{tab}{tab}file is image")
                    # optionale exif-Daten
                    if img.getexif():
                        extract_log.append(f"{tab}{tab}{tab}{tab}file has exif-header")
                        geo_exif_dict = {}
                        exif_dict = {TAGS[k]: v for k, v in img._getexif().items() if k in TAGS and (type(v) in [int, str] or TAGS[k] == 'GPSInfo')}
                        gps_info_value = exif_dict.get('GPSInfo', None)
                        if gps_info_value:
                            geo_exif_dict = {GPSTAGS[k]: v for k, v in gps_info_value.items() if k in GPSTAGS}

                            if geo_exif_dict.get('GPSLatitude'):
                                lat_tuple = geo_exif_dict.get('GPSLatitude')
                                if lat_tuple:
                                    # tuple with three floats: degree, minutes, seconds
                                    lat = float(lat_tuple[0]) + float(lat_tuple[1]) / 60 + float(lat_tuple[2]) / 3600
                                    # extract_log.append(f"{tab}{tab}{tab}{tab}{tab}GPSLatitude {lat}")

                            if geo_exif_dict.get('GPSLongitude'):
                                lon_tuple = geo_exif_dict.get('GPSLongitude')
                                if lon_tuple:
                                    # tuple with three floats: degree, minutes, seconds
                                    lon = float(lon_tuple[0]) + float(lon_tuple[1]) / 60 + float(lon_tuple[2]) / 3600
                                    # extract_log.append(f"{tab}{tab}{tab}{tab}{tab}GPSLongitude {lon}")

                            if geo_exif_dict.get('GPSAltitude'):
                                alt = float(geo_exif_dict.get('GPSAltitude'))
                                # extract_log.append(f"{tab}{tab}{tab}{tab}{tab}GPSAltitude {alt}")

                            if geo_exif_dict.get('GPSImgDirection'):
                                direction = float(geo_exif_dict.get('GPSImgDirection'))
                                # extract_log.append(f"{tab}{tab}{tab}{tab}{tab}GPSImgDirection {direction}")

                        if lat is not None and lon is not None:
                            extract_log.append(f"{tab}{tab}{tab}{tab}file is exif-gps-georeferenced")
                        else:
                            extract_log.append(f"{tab}{tab}{tab}{tab}file not georeferenced")
                    else:
                        extract_log.append(f"{tab}{tab}{tab}{tab}no exif-header")
            except:
                extract_log.append(f"{tab}{tab}{tab}{tab}file is no image")

            for meta_name, field_name in field_list.items():

                if preserve_existing and feature[field_name] not in [qgis.core.NULL, None, '']:
                    continue

                if meta_name == 'abs_path':
                    feature[field_name] = posix_path.as_posix()
                    feature_altered = True
                elif meta_name == 'rel_path' and pre_scan_rel_root_dir is not None:
                    try:
                        # Compute a version of this path relative to the path represented by other. If it’s impossible, ValueError is raised
                        rel_path = posix_path.relative_to(pre_scan_rel_root_dir)
                        rel_path = rel_path.parent
                        feature[field_name] = rel_path.as_posix()
                        feature_altered = True
                    except Exception as e:
                        pass
                elif meta_name == 'file_name':
                    feature[field_name] = posix_path.name
                    feature_altered = True
                elif meta_name == 'extension':
                    feature[field_name] = str.lower(posix_path.suffix).lstrip('.')
                    feature_altered = True
                elif meta_name == 'file_size':
                    feature[field_name] = stat_metas.st_size
                    feature_altered = True
                elif meta_name == 'file_hash':
                    feature[field_name] = MyTools.get_file_hash(posix_path, self.hash_alg)
                    feature_altered = True
                elif meta_name == 'm_time':
                    # mtime => Time of most recent content modification
                    # Datei-auf-Datenträger-Zeit, *nicht* Aufnahmezeit
                    feature[field_name] = QtCore.QDateTime.fromSecsSinceEpoch(int(stat_metas.st_mtime))
                    feature_altered = True
                elif meta_name == 'c_time':
                    # ctime => create/change-time
                    feature[field_name] = QtCore.QDateTime.fromSecsSinceEpoch(int(stat_metas.st_ctime))
                    feature_altered = True
                elif meta_name == 'a_time':
                    # atime => access-time
                    feature[field_name] = QtCore.QDateTime.fromSecsSinceEpoch(int(stat_metas.st_atime))
                    feature_altered = True
                elif meta_name == 'xmp_metas':
                    # xmp-Metadaten
                    # 'rb' => read binary, vermeidet "Ausnahme: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
                    with open(str(posix_path), 'rb') as fd:
                        d = str(fd.read())
                        xmp_start = d.find('<x:xmpmeta')
                        xmp_end = d.find('</x:xmpmeta')
                        xmp_str = d[xmp_start:xmp_end + 12]
                        # ersetzt die new-lines und tabs durch tatächliche Zeilenumrüche/Tabstops
                        xmp_metas = xmp_str.replace('\\n', '\n').replace('\\t', '\t')

                        feature[field_name] = xmp_metas
                        feature_altered = True
                elif meta_name == 'image_width':
                    if img:
                        feature[field_name] = img.width
                        feature_altered = True
                elif meta_name == 'image_height' and img:
                    if img:
                        feature[field_name] = img.height
                        feature_altered = True
                elif meta_name == 'iptc_metas':
                    if img:
                        # optionale iptc-Metadaten
                        iptc = IptcImagePlugin.getiptcinfo(img)
                        if iptc:
                            iptc_metas = ''
                            for iptc_key, iptc_value in iptc.items():
                                iptc_metas += f"{iptc_key} {iptc_value.decode('utf-8')}\n"
                            feature[field_name] = iptc_metas
                            feature_altered = True
                elif meta_name == 'exif_metas':
                    if exif_dict:
                        exif_metas = "Exif-Tags:\n"
                        for exif_key, exif_value in exif_dict.items():
                            # einige Inhalte binär
                            if type(exif_value) in [int, str]:
                                exif_metas += f"   {exif_key}: {exif_value}\n"

                        if geo_exif_dict:
                            exif_metas += "Geo-Tags:\n"
                            for exif_key, exif_value in geo_exif_dict.items():
                                exif_metas += f"   {exif_key}: {exif_value}\n"

                        feature[field_name] = exif_metas
                        feature_altered = True
                elif meta_name == 'date_time_original':
                    if exif_dict:
                        feature[field_name] = exif_dict.get('DateTimeOriginal', None)
                        feature_altered = True
                elif meta_name == 'gps_latitude':
                    if geo_exif_dict:
                        feature[field_name] = lat
                        feature_altered = True
                elif meta_name == 'gps_longitude':
                    if geo_exif_dict:
                        feature[field_name] = lon
                        feature_altered = True
                elif meta_name == 'gps_altitude':
                    if geo_exif_dict:
                        feature[field_name] = alt
                        feature_altered = True
                elif meta_name == 'gps_img_direction':
                    if geo_exif_dict:
                        feature[field_name] = direction
                        feature_altered = True
                else:
                    extract_log.append(f"<b>{tab}{tab}{tab}{tab}⭍ meta '{meta_name}' not implemented and ignored</b>")

            # geometry-calculation from exif-GPS
            if extract_gps_geom and lat is not None and lon is not None and tr_wgs_2_vl:
                if feature.hasGeometry() and feature.geometry().isGeosValid() and preserve_existing:
                    # extract_log.append(f"{tab}{tab}{tab}{tab}feature has valid geometry ➞ no geometry-update")
                    pass
                else:

                    if alt is not None:
                        geom = qgis._core.QgsGeometry.fromPoint(qgis._core.QgsPoint(lon, lat, alt))
                    else:
                        geom = qgis._core.QgsGeometry.fromPoint(qgis._core.QgsPoint(lon, lat))

                    if geom.isGeosValid():
                        geom.transform(tr_wgs_2_vl)
                        feature.setGeometry(geom)
                        feature_altered = True

                        extract_log.append(f"{tab}{tab}{tab}{tab}geometry updated from exif-gps-metas")

        else:
            extract_ok = False
            extract_log.append(f"<b>{tab}{tab}{tab}{tab}⭍ file not found '{posix_path.as_posix()}'</b>")

        return extract_ok, feature_altered, extract_log

    def get_extract_field(self, meta_name, field_name: str) -> qgis._core.QgsField:
        """wrapper to create a QgsField for specific meta, used to create table for pre-scan-layer
        :param meta_name: references self.extractable_file_metas
        :param field_name: user-defined field-name for the result-layer
        """
        # Rev. 2025-06-11

        field_metas = self.extractable_file_metas.get(meta_name)

        if field_metas:
            pre_scan_field = qgis._core.QgsField(field_name, field_metas['field_type'])
            return pre_scan_field

    def toggle_check_boxes(self, checked: bool):
        """convenience in pre-scan-widget: a checkbox in first cell of the QGridLayout to select/unselect all metas
        :param checked: status of the toggle-check-box
        """
        # Rev. 2025-06-11
        if self.pre_scan_widget:
            qcbs = self.pre_scan_widget.findChildren(QtWidgets.QCheckBox, options=QtCore.Qt.FindChildrenRecursively)
            for qcb in qcbs:
                meta_name = qcb.property('meta_name')
                if meta_name:
                    extract_meta = self.extractable_file_metas.get(meta_name)
                    # mandatory fields (abs_path) can't be unchecked
                    if extract_meta.get('mandatory'):
                        qcb.setChecked(True)
                    else:
                        qcb.setChecked(checked)

    def select_pre_scan_rel_root_dir(self, *arg, **kwargs):
        """shows directory-dialog for pre_scan_rel_root_dir, used for rel_path-calculation"""
        # Rev. 2025-06-11
        if self.qle_pre_scan_rel_root_dir:
            dlg_start_dir = self.qle_pre_scan_rel_root_dir.text()
            if not dlg_start_dir or not os.path.isdir(dlg_start_dir):
                dlg_start_dir = os.path.expanduser('~')
            pre_scan_rel_root_dir = QtWidgets.QFileDialog.getExistingDirectory(self.pre_scan_widget, 'select pre-scan-root-dir', dlg_start_dir, QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)
            self.qle_pre_scan_rel_root_dir.setText(pre_scan_rel_root_dir)

    def select_post_scan_rel_root_dir(self, *arg, **kwargs):
        """shows directory-dialog for post_scan_rel_root_dir, used for rel_path-calculation"""
        # Rev. 2025-06-11
        if self.qle_post_scan_rel_root_dir:
            dlg_start_dir = self.qle_post_scan_rel_root_dir.text()
            if not dlg_start_dir or not os.path.isdir(dlg_start_dir):
                dlg_start_dir = os.path.expanduser('~')
            post_scan_rel_root_dir = QtWidgets.QFileDialog.getExistingDirectory(self.post_scan_widget, 'select post-scan-root-dir', dlg_start_dir, QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)
            self.qle_post_scan_rel_root_dir.setText(post_scan_rel_root_dir)

    def parse_post_scan_widget(self) -> tuple:
        """parses the contents of self.post_scan_widget and returns a dictionary with metas of the selected extract-fields
        no checks
        :returns:
            post_scan_fields: dictionary key: meta_name, value: field_name (selected from existing layer => QComboBox)
            post_scan_rel_root_dir: path for relative path determination
            process_log: process-messages
        """
        # Rev. 2025-06-11
        post_scan_fields = {}
        post_scan_rel_root_dir = ''
        if self.post_scan_widget:
            for qcb in self.post_scan_widget.findChildren(QtWidgets.QComboBox, options=QtCore.Qt.FindChildrenRecursively):
                meta_name = qcb.property('meta_name')
                if meta_name:
                    field_name = qcb.currentText()
                    # no check for double-assign
                    if field_name:
                        post_scan_fields[meta_name] = field_name

            # relative-root-dir for rel_path-meta from QLineEdit
            for qle in self.post_scan_widget.findChildren(QtWidgets.QLineEdit, options=QtCore.Qt.FindChildrenRecursively):
                if qle.property('purpose') == 'post_scan_rel_root_dir':
                    post_scan_rel_root_dir = qle.text()
        return post_scan_fields, post_scan_rel_root_dir

    def parse_pre_scan_widget(self) -> tuple:
        """parses the contents of self.pre_scan_widget and returns a dictionary with metas of the selected extract-fields
        :returns:
            pre_scan_fields: dictionary key: meta_name, value: field_name (new layer, user-defined field-name => QLineEdit)
            pre_scan_rel_root_dir: path for relative path determination
            process_log: process-messages
        """
        # Rev. 2025-06-11
        pre_scan_fields = {}
        pre_scan_rel_root_dir = None
        if self.pre_scan_widget:
            qcbs = self.pre_scan_widget.findChildren(QtWidgets.QCheckBox, options=QtCore.Qt.FindChildrenRecursively)
            qles = self.pre_scan_widget.findChildren(QtWidgets.QLineEdit, options=QtCore.Qt.FindChildrenRecursively)
            qcb_dict = {}
            qle_dict = {}

            for qcb in qcbs:
                meta_name = qcb.property('meta_name')
                if meta_name:
                    qcb_dict[meta_name] = qcb

            for qle in qles:
                meta_name = qle.property('meta_name')
                if meta_name:
                    qle_dict[meta_name] = qle

                if qle.property('purpose') == 'pre_scan_rel_root_dir':
                    pre_scan_rel_root_dir = qle.text()

            for meta_name, qcb in qcb_dict.items():
                if qcb.isChecked():
                    field_name = qle_dict[meta_name].text()
                    if field_name:
                        pre_scan_fields[meta_name] = field_name

        return pre_scan_fields, pre_scan_rel_root_dir

    def get_post_scan_widget(self, post_scan_fields=None, post_scan_layer_id='', post_scan_abs_path_field='', post_scan_rel_root_dir='') -> QtWidgets.QWidget:
        """creates and returns self.post_scan_widget, a table-like widget with Grid-Layout that can be used as selector for extracted meta-data-fields in an existing layer
        :param post_scan_fields: current stored post_scan_fields, dictionary meta_name->field_name
        :param post_scan_layer_id: id of post_scan_layer
        :param post_scan_abs_path_field: field containing absolute-path, used to exclude this field as post-scan-target
        :param post_scan_rel_root_dir: root-directory for relative-path-calculation
        :returns: QWidget, which will be inserted/replaced in dialog
        """
        # Rev. 2025-06-11
        if post_scan_fields is None:
            post_scan_fields = {}

        int_types = [
            QtCore.QVariant.Int,
            QtCore.QVariant.LongLong,
            QtCore.QVariant.UInt,
            QtCore.QVariant.ULongLong,
        ]

        self.post_scan_widget = QtWidgets.QWidget()
        self.post_scan_widget.setLayout(QtWidgets.QGridLayout())

        if post_scan_layer_id:
            post_scan_layer = qgis._core.QgsProject.instance().mapLayer(post_scan_layer_id)
            if post_scan_layer:
                sub_row = 0
                self.post_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Meta</b>'), sub_row, 1)
                self.post_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Fieldname</b>'), sub_row, 2)
                self.post_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Type</b>'), sub_row, 3)
                self.post_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Description</b>'), sub_row, 4)

                for meta_name, extract_meta in self.extractable_file_metas.items():
                    # not extractable
                    if meta_name == 'abs_path':
                        continue

                    sub_row += 1

                    self.post_scan_widget.layout().addWidget(QtWidgets.QLabel(meta_name), sub_row, 1)

                    qcbx = QtWidgets.QComboBox()
                    qcbx.setProperty('meta_name', meta_name)
                    qcbx.setToolTip('select field for this meta-data')

                    qcbx.addItem('')
                    for field in post_scan_layer.dataProvider().fields():
                        if field.name() != post_scan_abs_path_field:
                            if field.type() == extract_meta.get('field_type') or (field.type() in int_types and extract_meta.get('field_type') in int_types):
                                qcbx.addItem(field.name())

                    MyTools.qcbx_select_by_value(qcbx, post_scan_fields.get(meta_name))

                    self.post_scan_widget.layout().addWidget(qcbx, sub_row, 2)

                    field_type = extract_meta.get('field_type')
                    self.post_scan_widget.layout().addWidget(QtWidgets.QLabel(QtCore.QMetaType.typeName(field_type)), sub_row, 3)

                    description = extract_meta.get('description')
                    ql = QtWidgets.QLabel()
                    ql.setOpenExternalLinks(True)
                    ql.setTextFormat(QtCore.Qt.RichText)
                    url = extract_meta.get('url')
                    if url:
                        description += f" <a href='{url}'>link</a>"
                        ql.setToolTip(url)

                    ql.setText(description)
                    self.post_scan_widget.layout().addWidget(ql, sub_row, 4)

                    # special meta rel_path, which requires an additional information (root-directory) and gets some extra widgets
                    if meta_name == 'rel_path':
                        sub_row += 1

                        sub_wdg = QtWidgets.QWidget()
                        sub_wdg.setLayout(QtWidgets.QHBoxLayout())
                        sub_wdg.setMaximumWidth(400)
                        sub_wdg.layout().addWidget(QtWidgets.QLabel('relative to: '))
                        self.qle_post_scan_rel_root_dir = QtWidgets.QLineEdit(self.post_scan_widget)
                        self.qle_post_scan_rel_root_dir.setText(post_scan_rel_root_dir)
                        self.qle_post_scan_rel_root_dir.setProperty('purpose', 'post_scan_rel_root_dir')
                        self.qle_post_scan_rel_root_dir.setReadOnly(True)
                        self.qle_post_scan_rel_root_dir.setToolTip('root-directory for relative-path')

                        sub_wdg.layout().addWidget(self.qle_post_scan_rel_root_dir)

                        qpb_select_post_scan_rel_root_dir = QtWidgets.QPushButton('...', self.post_scan_widget)
                        qpb_select_post_scan_rel_root_dir.setToolTip('click to specify root-directory')
                        qpb_select_post_scan_rel_root_dir.setMaximumWidth(50)
                        qpb_select_post_scan_rel_root_dir.setCursor(QtCore.Qt.PointingHandCursor)
                        qpb_select_post_scan_rel_root_dir.pressed.connect(self.select_post_scan_rel_root_dir)

                        sub_wdg.layout().addWidget(qpb_select_post_scan_rel_root_dir)

                        self.post_scan_widget.layout().addWidget(sub_wdg, sub_row, 2, 1, 3)

        return self.post_scan_widget

    def get_pre_scan_widget(self, checked_extract_fields=None, pre_scan_rel_root_dir='') -> QtWidgets.QWidget:
        """creates and returns self.pre_scan_widget, a table-like widget with Grid-Layout that can be used as selector for extracted meta-data-fields in a new layer
        :param checked_extract_fields: current stored extract_fields, dictionary meta_name->field_name
        :param pre_scan_rel_root_dir: scanned directory
        :returns: QWidget, which will be inserted/replaced in dialog
        """
        # Rev. 2025-06-11
        if checked_extract_fields is None:
            checked_extract_fields = {}

        self.pre_scan_widget = QtWidgets.QWidget()
        self.pre_scan_widget.setLayout(QtWidgets.QGridLayout())

        sub_row = 0
        qcb_select_all_metas = QtWidgets.QCheckBox()
        qcb_select_all_metas.toggled.connect(self.toggle_check_boxes)
        qcb_select_all_metas.setToolTip('Select all Fields')
        self.pre_scan_widget.layout().addWidget(qcb_select_all_metas, sub_row, 0)
        self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Meta</b>'), sub_row, 1)
        self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Fieldname</b>'), sub_row, 2)
        self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Type</b>'), sub_row, 3)
        self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel('<b>Description</b>'), sub_row, 4)

        for meta_name, extract_meta in self.extractable_file_metas.items():
            sub_row += 1
            qcb = QtWidgets.QCheckBox()
            qcb.setProperty('meta_name', meta_name)
            if extract_meta.get('mandatory'):
                qcb.setChecked(True)
                qcb.setDisabled(True)

            if meta_name in checked_extract_fields:
                qcb.setChecked(True)

            self.pre_scan_widget.layout().addWidget(qcb, sub_row, 0)
            self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel(meta_name), sub_row, 1)

            qle = QtWidgets.QLineEdit()
            qle.setProperty('meta_name', meta_name)

            if meta_name in checked_extract_fields:
                qle.setText(checked_extract_fields.get(meta_name))
            else:
                qle.setText(extract_meta.get('default_field_name'))

            qle.setMinimumWidth(100)
            qle.setToolTip('unique field-name for this meta-data')
            self.pre_scan_widget.layout().addWidget(qle, sub_row, 2)

            field_type = extract_meta.get('field_type')
            self.pre_scan_widget.layout().addWidget(QtWidgets.QLabel(QtCore.QMetaType.typeName(field_type)), sub_row, 3)

            description = extract_meta.get('description')
            ql = QtWidgets.QLabel()
            ql.setOpenExternalLinks(True)
            ql.setTextFormat(QtCore.Qt.RichText)
            url = extract_meta.get('url')
            if url:
                description += f" <a href='{url}'>link</a>"
                ql.setToolTip(url)

            ql.setText(description)
            self.pre_scan_widget.layout().addWidget(ql, sub_row, 4)

            # special meta rel_path, which requires an additional information (root-directory) and gets some extra widgets
            if meta_name == 'rel_path':
                sub_row += 1

                sub_wdg = QtWidgets.QWidget()
                sub_wdg.setLayout(QtWidgets.QHBoxLayout())
                sub_wdg.setMaximumWidth(400)
                sub_wdg.layout().addWidget(QtWidgets.QLabel('relative to: '))
                self.qle_pre_scan_rel_root_dir = QtWidgets.QLineEdit(self.pre_scan_widget)
                self.qle_pre_scan_rel_root_dir.setText(pre_scan_rel_root_dir)
                self.qle_pre_scan_rel_root_dir.setProperty('purpose', 'pre_scan_rel_root_dir')
                self.qle_pre_scan_rel_root_dir.setReadOnly(True)
                self.qle_pre_scan_rel_root_dir.setToolTip('root-directory for relative-path')

                sub_wdg.layout().addWidget(self.qle_pre_scan_rel_root_dir)

                qpb_select_pre_scan_rel_root_dir = QtWidgets.QPushButton('...', self.pre_scan_widget)
                qpb_select_pre_scan_rel_root_dir.setToolTip('click to specify root-directory')
                qpb_select_pre_scan_rel_root_dir.setMaximumWidth(50)
                qpb_select_pre_scan_rel_root_dir.setCursor(QtCore.Qt.PointingHandCursor)
                qpb_select_pre_scan_rel_root_dir.pressed.connect(self.select_pre_scan_rel_root_dir)

                sub_wdg.layout().addWidget(qpb_select_pre_scan_rel_root_dir)

                self.pre_scan_widget.layout().addWidget(sub_wdg, sub_row, 2, 1, 3)

        return self.pre_scan_widget


class StoredSettings:
    """Python-Class with properties used to store the user-defined FileSync-settings
    properties must be converted to strings when stored in ini-File"""

    # Rev. 2025-06-11
    _str_props = [
        'pre_scan_dir',
        'pre_scan_epsg',
        'pre_scan_patterns'
    ]

    def __init__(self):
        """constructor"""
        # Rev. 2025-06-11

        # PreScan-Settings
        self.pre_scan_dir = ''
        self.pre_scan_epsg = ''
        self.pre_scan_patterns = ''
        self.pre_scan_sub_dirs = True
        self.pre_scan_rel_root_dir = ''
        # dictionary meta_name -> field_name for pre-scan-table, will be stored in ini
        self.pre_scan_fields = {}

        # Sync-Settings
        self.sync_source_layer_id = ''
        self.sync_target_layer_id = ''
        self.sync_source_abs_path_field = ''
        self.sync_source_rel_path_field = ''
        self.sync_target_abs_path_field = ''
        self.sync_file_mode = ''
        self.sync_existing_file_mode = ''
        self.sync_existing_feature_mode = ''
        self.sync_target_dir = ''
        self.sync_update_geometries = False
        # dict, key: sync_target_field_name value: sync_source_field_name
        self.sync_fields = {}

        # PostScan-Settings
        self.post_scan_layer_id = ''
        self.post_scan_abs_path_field = ''
        self.post_scan_rel_root_dir = ''
        self.post_scan_preserve_existing = False
        self.post_scan_update_geometry_from_exif = False
        # dictionary meta_name -> field_name for post-scan-table, will be joined and stored in ini
        self.post_scan_fields = {}

    def __str__(self):
        """stringify, implemented for debug-purpose"""
        # Rev. 2025-06-11
        result_str = ''
        property_list = [prop for prop in dir(self) if not prop.startswith('_') and not callable(getattr(self, prop))]

        longest_prop = max(property_list, key=len)
        max_len = len(longest_prop)

        for prop in property_list:
            result_str += f"{prop:<{max_len}}    {getattr(self, prop)}\n"

        return result_str


class FileSync(object):
    """central Plugin-Object, returned from __init__.py classFactory()-Method"""

    # Rev. 2025-06-11

    # Nomenclature, functions beginning with...
    # dlg_* => dialog-functions, refresh parts of dialog...
    # s_* => slot-functions triggered by widgets in dialog
    # ssc_* => slot-functions for configuration-change affecting stored_settings
    # sys_* => system functions
    # tool_* => auxiliary functions

    def __init__(self, iface: qgis.gui.QgisInterface):
        """standard-to-implement-function for plugins, Constructor for the Plugin.
        Triggered
        a. on open QGis with activated plugin (even start QGis with blank project)
        b. on plugin-initialization
        :param iface: interface to running QGis-App
        """
        # Rev. 2025-06-11
        self.iface = iface
        self.my_dialog = None
        self.file_sync_toolbar = None
        self.qact_open_dialog = None
        self.qact_show_help = None

        self.ini_storage_file_name = '.QGis_FileSync_Plugin.ini'
        # delimiter-string for key-value-contents in ini-file, special character-combination, that should not be used in layer- or field-names
        # note: avoid '%', which raises configparser "invalid interpolation syntax"
        self.ini_delimiter = '|◁=▷|'

        # filled on sys_restore_settings, appended to log_history and shown with first dlg_init
        self.restore_settings_log = []

        # all necessary settings
        self.stored_settings = StoredSettings()

        # restore settings from last usage (ini-file)
        self.sys_restore_settings()

        # store signal-slot-connections for later remove
        self.project_connections = []

        # history of log-messages
        self.log_history = []

        # index of current show log for scroll-functionality
        self.crt_log_idx = 0

        # connect some signals in project to register TOC-changes (especially layersRemoved)
        # Note: legendLayersAdded instead of layersAdded because "Emitted, when a layer was added to the registry and the legend"
        # and legend-refresh uses QgsProject.instance().layerTreeRoot and not QgsProject.instance().mapLayers
        self.project_connections.append(qgis._core.QgsProject.instance().legendLayersAdded.connect(self.sys_project_legendLayersAdded, QtCore.Qt.UniqueConnection))
        self.project_connections.append(qgis._core.QgsProject.instance().layersRemoved.connect(self.sys_project_layersRemoved, QtCore.Qt.UniqueConnection))

        # identifier for two QgsAction
        self.georef_act_id = QtCore.QUuid('{fa3440e3-0464-431b-9c41-945d46433153}')
        self.show_file_act_id = QtCore.QUuid('{fa3440e3-0464-431b-9c41-945d46433154}')

        self.hash_alg = 'sha1'

        self.file_meta_extractor = FileMetaExtractor(self.hash_alg)

        self.digitize_map_tool = FeatureDigitizeMapTool(iface)

    def initGui(self):
        """"standard-to-implement-function: adapt/extend GUI
        Triggered
        a. on open QGis with activated plugin (even start QGis with blank project)
        b. on plugin-initialization
        """
        # Rev. 2025-06-11

        # Toolbar for the three actions qact_PolEvt qact_LolEvt and qact_ShowHelp
        self.file_sync_toolbar = self.iface.addToolBar('FileSyncToolbar')
        self.file_sync_toolbar.setObjectName('FileSyncToolbar')
        self.file_sync_toolbar.setToolTip('FileSync Toolbar')

        self.qact_open_dialog = QtWidgets.QAction(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/mActionHistory.svg'), 'Show FileSync-Dialog', self.iface.mainWindow())

        self.qact_open_dialog.triggered.connect(self.dlg_init)
        self.qact_open_dialog.setEnabled(True)
        self.qact_open_dialog.setToolTip('Show FileSync-Dialog')
        self.file_sync_toolbar.addAction(self.qact_open_dialog)
        # also in menubar
        self.iface.addPluginToMenu('FileSync', self.qact_open_dialog)

        self.qact_show_help = QtWidgets.QAction(QtGui.QIcon(f'{Path(__file__).resolve().parent}/icons/plugin-help.svg'), 'Show help', self.iface.mainWindow())
        self.qact_show_help.triggered.connect(self.tool_show_help)
        self.file_sync_toolbar.addAction(self.qact_show_help)
        self.iface.addPluginToMenu('FileSync', self.qact_show_help)
        self.qact_show_help.setToolTip('Show help (requires internet-connection)')

    def tool_show_help(self):
        """display help
        previous version used local documentation included in Plugin
        since version 2.0.1 no local helpfiles but use htmlpreview.github.io
        """
        # Rev. 2024-11-02
        if QtCore.QSettings().value('locale/overrideFlag', type=bool):
            lcid = QtCore.QSettings().value('locale/userLocale', 'en_US')
        else:
            # take settings from system-locale, independent from current app
            lcid = QtCore.QLocale.system().name()

        # lcid is a string composed of language, underscore and country
        # for the translation the language is sufficient:
        # 'de_DE', 'de_AT', 'de_CH', 'de_BE', 'de_LI'... -> 'de'
        # 'en_US', 'en_GB'... -> 'en'
        lcid_language = lcid[0:2]

        help_url = 'https://htmlpreview.github.io/?https://github.com/Ludwig-K/QGisFileSync/blob/main/docs/index.en.html'

        if lcid_language == 'de':
            help_url = 'https://htmlpreview.github.io/?https://github.com/Ludwig-K/QGisFileSync/blob/main/docs/index.de.html'

        webbrowser.open(help_url, new=2)

    def sys_project_legendLayersAdded(self):
        """triggered by qgis._core.QgsProject.instance().legendLayersAdded
        nearly the same as layersAdded"""
        # Rev. 2025-06-11
        self.dlg_refresh_sync_layers()
        self.dlg_refresh_post_scan_layers()
        self.dlg_refresh_layer_action_layers()

    def sys_project_layersRemoved(self, removed_layer_ids: typing.Iterable[str]):
        """triggered by qgis._core.QgsProject.instance().layersRemoved
        also triggered on project-close
        check settings, refresh dialog
        :param removed_layer_ids: List of removed layer-IDs, mostly only one
        """
        # Rev. 2025-06-11

        for layer_id in removed_layer_ids:
            # a check against derived layer after delete raises
            # => RuntimeError: wrapped C/C++ object of type QgsVectorLayer has been deleted.

            if layer_id == self.stored_settings.sync_source_layer_id:
                self.stored_settings.sync_source_layer_id = ''

            if layer_id == self.stored_settings.sync_target_layer_id:
                self.stored_settings.sync_target_layer_id = ''

            if layer_id == self.stored_settings.post_scan_layer_id:
                self.stored_settings.post_scan_layer_id = ''

        self.dlg_refresh_post_scan_layers()
        self.dlg_refresh_sync_layers()
        self.dlg_refresh_layer_action_layers()

    def dlg_init(self):
        """initializes on first call or opens previously closed dialog"""
        # Rev. 2025-06-11
        if self.my_dialog:
            # re-open existing dialog
            # Note: closed dialogs are only hidden
            self.my_dialog.show()
            self.my_dialog.setFocus()
            # if its tabbed:
            self.my_dialog.raise_()
        else:
            # first call, no dialog so far => init, register signal/slot
            self.my_dialog = FileSyncDialog(self.iface)

            # ...docked to QGis-Main-Window
            self.iface.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.my_dialog)
            self.my_dialog.setFloating(True)

            # signal/slot-connections
            # self.my_dialog.tbw_central.currentChanged.connect(self.dlg_tbw_central_changed)

            # PreScan
            self.my_dialog.qpb_select_pre_scan_dir.pressed.connect(self.scc_select_pre_scan_dir)
            self.my_dialog.qle_pre_scan_dir.mousePressEvent = self.scc_select_pre_scan_dir
            self.my_dialog.qpb_select_pre_scan_crs.pressed.connect(self.scc_select_pre_scan_crs)
            self.my_dialog.qle_pre_scan_epsg.mousePressEvent = self.scc_select_pre_scan_crs
            self.my_dialog.qcb_select_pre_scan_patterns.currentIndexChanged.connect(self.scc_select_pre_scan_patterns)
            self.my_dialog.qpb_start_pre_scan.pressed.connect(self.s_start_pre_scan)

            # Sync
            self.my_dialog.qpb_refresh_sync_layers.pressed.connect(self.dlg_refresh_sync_layers)
            self.my_dialog.qcbn_sync_source_layer.currentIndexChanged.connect(self.scc_select_sync_source_lyr)
            self.my_dialog.qcbn_sync_target_layer.currentIndexChanged.connect(self.scc_select_sync_target_lyr)
            self.my_dialog.qpb_select_sync_target_dir.pressed.connect(self.scc_select_sync_target_dir)
            self.my_dialog.qle_sync_target_dir.mousePressEvent = self.scc_select_sync_target_dir
            self.my_dialog.qpb_open_sync_source_table.pressed.connect(self.s_open_sync_source_table)
            self.my_dialog.qpb_open_sync_target_table.pressed.connect(self.s_open_sync_target_table)
            self.my_dialog.qlw_sync_source_layer_fields.itemSelectionChanged.connect(self.dlg_source_layer_fields_selection_changed)
            self.my_dialog.qpb_add_sync_mapping.clicked.connect(self.dlg_add_sync_mapping)
            self.my_dialog.qpb_clear_sync_mappings.clicked.connect(self.scc_clear_sync_mappings)
            # delete-icon in last column
            self.my_dialog.qtw_sync_mappings.itemClicked.connect(self.dlg_qtw_sync_mappings_clicked)
            self.my_dialog.qcb_sync_source_abs_path_field.currentIndexChanged.connect(self.scc_select_sync_source_abs_path_field)
            self.my_dialog.qcb_sync_source_rel_path_field.currentIndexChanged.connect(self.scc_select_sync_source_rel_path_field)
            self.my_dialog.qcb_sync_target_abs_path_field.currentIndexChanged.connect(self.scc_select_sync_target_abs_path_field)
            self.my_dialog.qcb_sync_existing_file_mode.currentIndexChanged.connect(self.scc_select_sync_existing_file_mode)
            self.my_dialog.qcb_sync_existing_feature_mode.currentIndexChanged.connect(self.scc_select_sync_existing_feature_mode)
            self.my_dialog.qrb_sync_file_mode_keep.toggled.connect(self.scc_qrb_sync_file_mode_keep_toggled)
            self.my_dialog.qrb_sync_file_mode_copy.toggled.connect(self.scc_qrb_sync_file_mode_copy_toggled)
            self.my_dialog.qcb_sync_update_geometries.toggled.connect(self.scc_qcb_sync_update_geometries_toggled)
            self.my_dialog.qpb_start_sync.clicked.connect(self.s_start_sync)

            # PostScan
            self.my_dialog.qpb_open_post_scan_layer.clicked.connect(self.s_open_post_scan_layer)
            self.my_dialog.qpb_refresh_post_scan_layer.clicked.connect(self.dlg_refresh_post_scan_layers)
            self.my_dialog.qcbn_post_scan_layer.currentIndexChanged.connect(self.scc_select_post_scan_layer)
            self.my_dialog.qcb_post_scan_abs_path_field.currentIndexChanged.connect(self.scc_select_post_scan_abs_path_field)
            self.my_dialog.qcb_post_scan_preserve_existing.toggled.connect(self.scc_qcb_post_scan_preserve_existing_toggled)
            self.my_dialog.qcb_post_scan_update_geometry_from_exif.toggled.connect(self.scc_qcb_post_scan_update_geometry_from_exif)

            # Log
            self.my_dialog.qpb_start_post_scan.clicked.connect(self.s_start_post_scan)
            self.my_dialog.qpb_skip_log_back.clicked.connect(self.dlg_skip_log_back)
            self.my_dialog.qpb_skip_log_for.clicked.connect(self.dlg_skip_log_for)
            self.my_dialog.qpb_clear_log.clicked.connect(self.dlg_clear_log)

            # LayerActions
            self.my_dialog.qcbn_layer_action_layer.currentIndexChanged.connect(self.dlg_refresh_layer_action_fields)
            self.my_dialog.qpb_open_layer_action_layer.clicked.connect(self.s_open_layer_action_layer)
            self.my_dialog.qpb_add_layer_actions.clicked.connect(self.s_add_layer_actions)
            self.my_dialog.qpb_remove_layer_actions.clicked.connect(self.s_remove_layer_actions)

            # restore-settings is called *before* dialog is initialized, so delayed show of restore_settings_log
            self.tool_append_to_log_history(self.restore_settings_log, False)

            self.dlg_refresh_layer_action_layers()

        # show all settings in dialog:
        self.dlg_show_stored_settings()

    def dlg_show_stored_settings(self, use_cases=None):
        """Show current stored_settings in dialog
        :param use_cases: if None, all three Tabs of dialog are refreshed
        """
        # Rev. 2025-06-11
        if not use_cases:
            use_cases = ['PRE_SCAN_SETTINGS', 'SYNC_SETTINGS', 'POST_SCAN_SETTINGS']

        if 'PRE_SCAN_SETTINGS' in use_cases:
            self.my_dialog.qle_pre_scan_dir.setText(self.stored_settings.pre_scan_dir)
            self.my_dialog.qle_pre_scan_epsg.setText(self.stored_settings.pre_scan_epsg)
            self.my_dialog.qle_pre_scan_patterns.setText(self.stored_settings.pre_scan_patterns)
            self.my_dialog.qcb_pre_scan_sub_dirs.setChecked(self.stored_settings.pre_scan_sub_dirs)
            self.file_meta_extractor.get_pre_scan_widget(self.stored_settings.pre_scan_fields, self.stored_settings.pre_scan_rel_root_dir)
            self.my_dialog.qsa_pre_scan.setWidget(self.file_meta_extractor.pre_scan_widget)

        if 'SYNC_SETTINGS' in use_cases:
            self.dlg_refresh_sync_layers()
            self.dlg_refresh_qtw_sync_mappings()
            self.dlg_refresh_sync_source_fields()
            self.dlg_refresh_sync_target_fields()
            self.my_dialog.qle_sync_target_dir.setText(self.stored_settings.sync_target_dir)
            self.dlg_show_sync_mode()
            self.my_dialog.qcb_sync_update_geometries.setChecked(self.stored_settings.sync_update_geometries)
            self.tmr_resize_sync_cols = QtCore.QTimer()
            self.tmr_resize_sync_cols.timeout.connect(self.dlg_resize_sync_cols)
            self.tmr_resize_sync_cols.setSingleShot(True)
            self.tmr_resize_sync_cols.start(200)
            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_existing_file_mode, self.stored_settings.sync_existing_file_mode, QtCore.Qt.UserRole)
            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_existing_feature_mode, self.stored_settings.sync_existing_feature_mode, QtCore.Qt.UserRole)
            # two times, see dlg_refresh_sync_source_fields
            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_source_rel_path_field, self.stored_settings.sync_source_rel_path_field)

        if 'POST_SCAN_SETTINGS' in use_cases:
            self.dlg_refresh_post_scan_layers()
            self.dlg_refresh_post_scan_layer_fields()
            self.my_dialog.qcb_post_scan_preserve_existing.setChecked(self.stored_settings.post_scan_preserve_existing)
            self.my_dialog.qcb_post_scan_update_geometry_from_exif.setChecked(self.stored_settings.post_scan_update_geometry_from_exif)
            self.file_meta_extractor.get_post_scan_widget(self.stored_settings.post_scan_fields, self.stored_settings.post_scan_layer_id, self.stored_settings.post_scan_abs_path_field, self.stored_settings.post_scan_rel_root_dir)
            self.my_dialog.qsa_post_scan.setWidget(self.file_meta_extractor.post_scan_widget)

    def dlg_resize_sync_cols(self):
        """tricky: QGridLayout-align the qlw_sync_source_layer_fields and qlw_sync_target_layer_fields (no columnSpan) of the with the contents of qtw_sync_mappings (columnSpan 4)"""
        # Rev. 2025-06-11
        # the two widgets in grid_container_wdg above qtw_sync_mappings:
        col_width_0 = self.my_dialog.qlw_sync_source_layer_fields.geometry().width()
        col_width_1 = self.my_dialog.qlw_sync_target_layer_fields.geometry().width()

        # relative width:
        col_width_0_rel = col_width_0 / (col_width_0 + col_width_1)
        col_width_1_rel = col_width_1 / (col_width_0 + col_width_1)

        # qtw_sync_mappings-width - 20px row-header -15 px arrow - 30 px delete
        qtw_available_width = self.my_dialog.qtw_sync_mappings.geometry().width() - 65

        # proportionally distibuted:
        self.my_dialog.qtw_sync_mappings.setColumnWidth(0, int(col_width_0_rel * qtw_available_width))
        # arrow:
        # self.my_dialog.qtw_sync_mappings.setColumnWidth(1, 15)
        self.my_dialog.qtw_sync_mappings.setColumnWidth(2, int(col_width_1_rel * qtw_available_width))
        # delete:
        # self.my_dialog.qtw_sync_mappings.setColumnWidth(2, 30)

    def scc_qrb_sync_file_mode_keep_toggled(self, checked):
        """sync_file_mode is symbolized in dialog with two radio-buttons
        dependend on sync_file_mode some areas of the dialog will get disabled
        additionally parsed by dlg_parse_settings"""
        # Rev. 2025-06-11
        if checked:
            self.stored_settings.sync_file_mode = 'keep'
        self.dlg_show_sync_mode()

    def scc_qrb_sync_file_mode_copy_toggled(self, checked):
        """sync_file_mode is symbolized in dialog with two radio-buttons
        dependend on sync_file_mode some areas of the dialog will get disabled
        additionally parsed by dlg_parse_settings"""
        # Rev. 2025-06-11
        if checked:
            self.stored_settings.sync_file_mode = 'copy'
        self.dlg_show_sync_mode()

    def scc_qcb_sync_update_geometries_toggled(self, checked):
        """sets sync_update_geometries from QCheckBox
        additionally parsed by dlg_parse_settings"""
        # Rev. 2025-06-11
        self.stored_settings.sync_update_geometries = checked

    def scc_qcb_post_scan_preserve_existing_toggled(self, checked):
        """sets post_scan_preserve_existing from QCheckBox
        additionally parsed by dlg_parse_settings"""
        # Rev. 2025-06-11
        self.stored_settings.post_scan_preserve_existing = checked

    def scc_qcb_post_scan_update_geometry_from_exif(self, checked):
        """sets post_scan_update_geometry_from_exif from QCheckBox
        additionally parsed by dlg_parse_settings"""
        # Rev. 2025-06-11

        self.stored_settings.post_scan_update_geometry_from_exif = checked

    def dlg_show_sync_mode(self):
        """shows self.stored_settings.sync_file_mode in dialog
        dependend on sync_file_mode some areas of the dialog will get disabled"""
        # Rev. 2025-05-30
        with QtCore.QSignalBlocker(self.my_dialog.qrb_sync_file_mode_keep):
            self.my_dialog.qrb_sync_file_mode_keep.setChecked(self.stored_settings.sync_file_mode == 'keep')

        with QtCore.QSignalBlocker(self.my_dialog.qrb_sync_file_mode_copy):
            self.my_dialog.qrb_sync_file_mode_copy.setChecked(self.stored_settings.sync_file_mode == 'copy')

        # convenience: enable/disable dialog-area for sync_file_mode 'copy'
        toggle_rows = [7, 8, 9]
        toggle_cols = [0, 1, 2, 3, 4, 5, 6]
        for sub_row in toggle_rows:
            for sub_col in toggle_cols:
                qli = self.my_dialog.grid_container_wdg.layout().itemAtPosition(sub_row, sub_col)
                if qli:
                    qli.widget().setEnabled(self.stored_settings.sync_file_mode == 'copy')

    def scc_select_sync_source_abs_path_field(self, idx):
        """parses sync_source_abs_path_field from qcb_sync_source_abs_path_field"""
        # Rev. 2025-06-11
        self.stored_settings.sync_source_abs_path_field = self.my_dialog.qcb_sync_source_abs_path_field.currentText()
        self.dlg_refresh_sync_source_fields()

    def scc_select_sync_source_rel_path_field(self, idx):
        """parses sync_source_rel_path_field from qcb_sync_source_rel_path_field"""
        # Rev. 2025-06-11
        self.stored_settings.sync_source_rel_path_field = self.my_dialog.qcb_sync_source_rel_path_field.currentText()
        self.dlg_refresh_sync_source_fields()

    def scc_select_sync_target_abs_path_field(self, idx):
        """parses and checks sync_target_abs_path_field from qcb_sync_target_abs_path_field"""
        # Rev. 2025-06-11
        self.stored_settings.sync_target_abs_path_field = self.my_dialog.qcb_sync_target_abs_path_field.currentText()
        if self.stored_settings.sync_target_abs_path_field in self.stored_settings.sync_fields:
            del self.stored_settings.sync_fields[self.stored_settings.sync_target_abs_path_field]
            self.iface.messageBar().pushMessage("FileSync", f"Remove Field '{self.stored_settings.sync_target_abs_path_field}' from registered Mappings", level=qgis._core.Qgis.Info, duration=5)
            self.dlg_refresh_qtw_sync_mappings()

        self.dlg_refresh_sync_target_fields()

    def scc_select_post_scan_abs_path_field(self, idx):
        """parses post_scan_abs_path_field from qcb_post_scan_abs_path_field"""
        # Rev. 2025-06-11
        self.stored_settings.post_scan_abs_path_field = self.my_dialog.qcb_post_scan_abs_path_field.currentText()

    def scc_select_post_scan_layer(self):
        """selects self.stored_settings.post_scan_layer_id and refreshes dependend field-select-QComboBoxes and file_meta_extractor.post_scan_widget"""
        # Rev. 2025-06-11
        self.stored_settings.post_scan_layer_id = ''
        post_scan_layer = self.my_dialog.qcbn_post_scan_layer.currentData(Qt_Roles.RETURN_VALUE)
        if post_scan_layer:
            self.stored_settings.post_scan_layer_id = post_scan_layer.id()
            self.dlg_refresh_post_scan_layer_fields()
            self.file_meta_extractor.get_post_scan_widget(self.stored_settings.post_scan_fields, self.stored_settings.post_scan_layer_id, self.stored_settings.post_scan_abs_path_field, self.stored_settings.post_scan_rel_root_dir)
            self.my_dialog.qsa_post_scan.setWidget(self.file_meta_extractor.post_scan_widget)

    def s_open_layer_action_layer(self):
        vl = self.my_dialog.qcbn_layer_action_layer.currentData(Qt_Roles.RETURN_VALUE)
        if vl:
            MyTools.re_open_attribute_tables(self.iface, vl, True)

    def s_remove_layer_actions(self):
        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3
        process_log = []
        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} removeLayerActions")
        vl = self.my_dialog.qcbn_layer_action_layer.currentData(Qt_Roles.RETURN_VALUE)
        if vl and isinstance(vl, qgis._core.QgsVectorLayer):
            action_list = [action for action in vl.actions().actions() if action.id() == FeatureDigitizeMapTool.show_form_act_id]
            for action in action_list:
                vl.actions().removeAction(action.id())
                process_log.append(f"{tab}✔ ShowForm-Action for layer '{vl.name()}' removed")

            action_list = [action for action in vl.actions().actions() if action.id() == FeatureDigitizeMapTool.show_file_act_id]
            for action in action_list:
                vl.actions().removeAction(action.id())
                process_log.append(f"{tab}✔ ShowFile-action for layer '{vl.name()}' removed")

            action_list = [action for action in vl.actions().actions() if action.id() == FeatureDigitizeMapTool.georef_act_id]
            for action in action_list:
                vl.actions().removeAction(action.id())
                process_log.append(f"{tab}✔ ShowFeature-Action '{action.id()}' for layer '{vl.name()}' removed")

            #MyTools.re_open_attribute_tables(self.iface, vl, True)
            vl.reload()
        else:
            process_log.append(f"<b>{tab}⭍ No layer selected, no actions removed</b>")

        self.tool_append_to_log_history(process_log)

    def s_add_layer_actions(self):
        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3
        process_log = []
        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} addLayerActions")

        string_types = [
            QtCore.QVariant.String,
            QtCore.QMetaType.QString,
        ]

        double_types = [
            QtCore.QVariant.Double,
            QtCore.QMetaType.Double
        ]

        date_time_types = [
            QtCore.QVariant.DateTime,
            QtCore.QMetaType.QDateTime
        ]

        vl = self.my_dialog.qcbn_layer_action_layer.currentData(Qt_Roles.RETURN_VALUE)
        if vl and isinstance(vl, qgis._core.QgsVectorLayer):

            FeatureDigitizeMapTool.add_show_form_action(vl)
            process_log.append(f"{tab}✔ ShowForm-action for layer '{vl.name()}' added")

            abs_path_field_name = self.my_dialog.qcbx_layer_action_abs_path_field.currentData()
            checked_abs_path_field_name = ''
            show_file_action_added = False
            if abs_path_field_name:
                fnx = vl.fields().indexOf(abs_path_field_name)
                if fnx >= 0:
                    abs_path_field = vl.fields()[fnx]
                    if abs_path_field.type() in string_types:
                        checked_abs_path_field_name = abs_path_field_name
                        FeatureDigitizeMapTool.add_show_file_action(vl, checked_abs_path_field_name)
                        process_log.append(f"{tab}✔ ShowFile-action for layer '{vl.name()}' added")
                        process_log.append(f"{tab}{tab}abs-path-field '{checked_abs_path_field_name}'")
                        show_file_action_added = True

            if not show_file_action_added:
                action_list = [action for action in vl.actions().actions() if action.id() == FeatureDigitizeMapTool.show_file_act_id]
                if action_list:
                    for action in action_list:
                        vl.actions().removeAction(action.id())

                process_log.append(f"{tab}⯑ abs-path-field missing/not found/wrong type ➞ ShowFile-action for layer '{vl.name()}' removed")

            checked_direction_field_name = ''
            checked_last_edit_date_time_field_name = ''

            show_feature_action_added = False
            if vl.geometryType() == qgis._core.Qgis.GeometryType.Point:
                direction_field_name = self.my_dialog.qcbx_layer_action_direction_field.currentData()
                if direction_field_name:
                    fnx = vl.fields().indexOf(direction_field_name)
                    if fnx >= 0:
                        direction_field = vl.fields()[fnx]
                        if direction_field.type() in double_types:
                            checked_direction_field_name = direction_field_name

                last_edit_date_time_field_name = self.my_dialog.qcbx_layer_action_last_edit_date_time_field.currentData()
                if last_edit_date_time_field_name:
                    fnx = vl.fields().indexOf(last_edit_date_time_field_name)
                    if fnx >= 0:
                        last_edit_date_time_field = vl.fields()[fnx]
                        if last_edit_date_time_field.type() in date_time_types:
                            checked_last_edit_date_time_field_name = last_edit_date_time_field_name

                FeatureDigitizeMapTool.add_show_feature_action(vl, checked_direction_field_name, checked_last_edit_date_time_field_name)
                process_log.append(f"{tab}✔ ShowFeature-action for layer '{vl.name()}' added")
                show_feature_action_added = True
                if checked_direction_field_name:
                    process_log.append(f"{tab}{tab}direction-field '{checked_direction_field_name}'")
                if checked_last_edit_date_time_field_name:
                    process_log.append(f"{tab}{tab}last-edit-date-time-field '{checked_last_edit_date_time_field_name}'")

            if not show_feature_action_added:
                action_list = [action for action in vl.actions().actions() if action.id() == FeatureDigitizeMapTool.georef_act_id]
                if action_list:
                    for action in action_list:
                        vl.actions().removeAction(action.id())

                process_log.append(f"{tab}⯑ wrong geometry type ➞ ShowFeature-action for layer '{vl.name()}' removed")

            #MyTools.re_open_attribute_tables(self.iface, vl, True)
            vl.reload()
        else:
            process_log.append(f"<b>{tab}⭍ No layer selected, no actions added</b>")

        self.tool_append_to_log_history(process_log)

    def dlg_refresh_layer_action_fields(self):
        vl = self.my_dialog.qcbn_layer_action_layer.currentData(Qt_Roles.RETURN_VALUE)

        self.my_dialog.qcbx_layer_action_abs_path_field.blockSignals(True)
        self.my_dialog.qcbx_layer_action_direction_field.blockSignals(True)
        self.my_dialog.qcbx_layer_action_last_edit_date_time_field.blockSignals(True)

        self.my_dialog.qcbx_layer_action_abs_path_field.clear()
        self.my_dialog.qcbx_layer_action_abs_path_field.addItem('')

        self.my_dialog.qcbx_layer_action_direction_field.clear()
        self.my_dialog.qcbx_layer_action_direction_field.addItem('')

        self.my_dialog.qcbx_layer_action_last_edit_date_time_field.clear()
        self.my_dialog.qcbx_layer_action_last_edit_date_time_field.addItem('')

        if vl:
            string_types = [
                QtCore.QVariant.String,
                QtCore.QMetaType.QString,
            ]

            double_types = [
                QtCore.QVariant.Double,
                QtCore.QMetaType.Double
            ]
            date_time_types = [
                QtCore.QVariant.DateTime,
                QtCore.QMetaType.QDateTime
            ]

            # tricky for convenience:
            # scan layer-actions and find current assigned fields,
            # pre-select the QComboBox'es and
            # show current configuration for the selected layer
            # @TothinkAbout: scan command with regex
            action_list_show_feature = [action for action in vl.actions().actions() if action.id() in [FeatureDigitizeMapTool.georef_act_id]]
            action_list_show_file = [action for action in vl.actions().actions() if action.id() in [FeatureDigitizeMapTool.show_file_act_id]]

            current_abs_path_field = None
            current_direction_field = None
            current_last_edit_date_time_field = None

            last_action_show_feature_command = ''
            if action_list_show_feature:
                last_action_show_feature = action_list_show_feature.pop()
                last_action_show_feature_command = last_action_show_feature.command()

            last_action_show_file_command = ''
            if action_list_show_file:
                last_action_show_file = action_list_show_file.pop()
                last_action_show_file_command = last_action_show_file.command()

            for field in vl.dataProvider().fields():
                if field.type() in string_types:
                    self.my_dialog.qcbx_layer_action_abs_path_field.addItem(field.name(), field.name())
                    if f"abs_path_field_name='{field.name()}'" in last_action_show_file_command:
                        current_abs_path_field = field.name()

                elif field.type() in double_types:
                    self.my_dialog.qcbx_layer_action_direction_field.addItem(field.name(), field.name())
                    if f"direction_field_name='{field.name()}'" in last_action_show_feature_command:
                        current_direction_field = field.name()

                elif field.type() in date_time_types:
                    self.my_dialog.qcbx_layer_action_last_edit_date_time_field.addItem(field.name(), field.name())
                    if f"last_edit_date_time_field_name='{field.name()}'" in last_action_show_feature_command:
                        current_last_edit_date_time_field = field.name()

            MyTools.qcbx_select_by_value(self.my_dialog.qcbx_layer_action_abs_path_field, current_abs_path_field)
            MyTools.qcbx_select_by_value(self.my_dialog.qcbx_layer_action_direction_field, current_direction_field)
            MyTools.qcbx_select_by_value(self.my_dialog.qcbx_layer_action_last_edit_date_time_field, current_last_edit_date_time_field)

        self.my_dialog.qcbx_layer_action_abs_path_field.blockSignals(False)
        self.my_dialog.qcbx_layer_action_direction_field.blockSignals(False)
        self.my_dialog.qcbx_layer_action_last_edit_date_time_field.blockSignals(False)

    def dlg_skip_log_back(self):
        """shows previous log in self.my_dialog.qte_log"""
        # Rev. 2025-06-11
        self.my_dialog.qte_log.clear()
        if self.log_history:
            self.crt_log_idx -= 1
            max_idx = len(self.log_history) - 1
            self.crt_log_idx = max(0, min(max_idx, self.crt_log_idx))
            log_string = self.log_history[self.crt_log_idx]
            self.my_dialog.qte_log.insertHtml(log_string)

    def dlg_skip_log_for(self):
        """shows next log in self.my_dialog.qte_log"""
        # Rev. 2025-06-11
        self.my_dialog.qte_log.clear()
        if self.log_history:
            self.crt_log_idx += 1
            max_idx = len(self.log_history) - 1
            self.crt_log_idx = max(0, min(max_idx, self.crt_log_idx))
            log_string = self.log_history[self.crt_log_idx]
            self.my_dialog.qte_log.insertHtml(log_string)

    def dlg_clear_log(self):
        """clears self.my_dialog.qte_log and resets log_history"""
        # Rev. 2025-06-11
        self.my_dialog.qte_log.clear()
        self.log_history = []
        self.crt_log_idx = 0

    def tool_append_to_log_history(self, log_list, show_log_tab=True):
        """some long running processes generate log-messages with user-infos, errors... in form of lists
        theses are concatenated to html-strings, appended to self.log_history and shown in self.my_dialog.qte_log"""
        # Rev. 2025-06-11
        log_string = '<br/>'.join(log_list)
        self.log_history.append(log_string)
        self.crt_log_idx = len(self.log_history) - 1
        if self.my_dialog:
            self.my_dialog.qte_log.clear()
            self.my_dialog.qte_log.insertHtml(log_string)
            if show_log_tab:
                self.my_dialog.tbw_central.setCurrentIndex(4)

    def s_start_post_scan(self):
        """starts PostScan-Process"""
        # Rev. 2025-06-11
        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3
        process_log = []
        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} start PostScan")
        self.dlg_parse_settings(['POST_SCAN_SETTINGS'])
        check_ok, check_log = self.sys_check_settings(['POST_SCAN_SETTINGS'])
        process_log += check_log
        if check_ok:
            post_scan_layer = self.tool_get_post_scan_layer()

            if post_scan_layer.isEditable():
                num_features = post_scan_layer.featureCount()

                self.my_dialog.sub_wdg_post_scan_progress.setVisible(True)
                self.my_dialog.qprb_post_scan.setMinimum(0)
                self.my_dialog.qprb_post_scan.setMaximum(num_features)
                self.my_dialog.qprb_post_scan.setValue(0)
                self.my_dialog.qlbl_post_scan_progress.setText('')

                process_log.append(f"{tab}Feature-Iteration-Start, {num_features} features")
                fc = 0
                success_fids = []
                unchanged_fids = []
                missing_file_fids = []
                skip_fids = []

                wgs_84_crs = qgis._core.QgsCoordinateReferenceSystem("EPSG:4326")
                tr_wgs_2_vl = qgis._core.QgsCoordinateTransform(wgs_84_crs, post_scan_layer.crs(), qgis._core.QgsProject.instance())

                for post_scan_feature in post_scan_layer.getFeatures():
                    fc += 1
                    self.my_dialog.qprb_post_scan.setValue(fc)
                    self.my_dialog.qlbl_post_scan_progress.setText(f"Feature {fc} from {num_features}")
                    abs_path_str = post_scan_feature[self.stored_settings.post_scan_abs_path_field]
                    abs_path_posix = Path(abs_path_str)
                    process_log.append(f"{tab}{tab} #{post_scan_feature.id()} '{abs_path_posix.as_posix()}'")

                    if abs_path_posix.is_file():
                        process_log.append(f"{tab}{tab}{tab}✔ file exists")
                        extract_ok, feature_altered, extract_log = self.file_meta_extractor.extract_file_metas(abs_path_posix, post_scan_feature, self.stored_settings.post_scan_fields, self.stored_settings.post_scan_rel_root_dir, self.stored_settings.post_scan_preserve_existing, self.stored_settings.post_scan_update_geometry_from_exif, tr_wgs_2_vl)
                        process_log += extract_log
                        if extract_ok:
                            if feature_altered:
                                post_scan_layer.updateFeature(post_scan_feature)
                                process_log.append(f"{tab}{tab}{tab}✔ feature updated")
                                success_fids.append(post_scan_feature.id())
                            else:
                                process_log.append(f"{tab}{tab}{tab}✔ feature not altered, no update")
                                unchanged_fids.append(post_scan_feature.id())
                        else:
                            process_log.append(f"<b>{tab}{tab}{tab}⭍ extract-metas failed, no update</b>")
                            skip_fids.append(post_scan_feature.id())
                    else:
                        process_log.append(f"<b>{tab}{tab}{tab}⭍ file not found, check path</b>")
                        missing_file_fids.append(post_scan_feature.id())

                process_log.append(f"{tab}...Feature-Iteration-End")

                process_log.append(f"{tab}{len(success_fids)} features updated")
                process_log.append(f"{tab}{len(unchanged_fids)} features unchanged, no update")
                if missing_file_fids:
                    process_log.append(f"{tab}{len(missing_file_fids)} features with missing files skipped and selected")

                if skip_fids:
                    process_log.append(f"{tab}{len(skip_fids)} features for other reasons skipped and selected")

                debug_log(missing_file_fids + skip_fids)

                post_scan_layer.selectByIds(missing_file_fids + skip_fids)


            else:
                process_log.append(f"<b>{tab}⭍ PostScanLayer not editable, PostScan aborted</b>")

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} end PostScan, runtime {(time.perf_counter_ns() - t_1) * 1e-9:.5f} s")

        self.tool_append_to_log_history(process_log)

    def s_start_sync(self):
        """starts Sync-Process"""
        # Rev. 2025-06-11

        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3
        process_log = []

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} start synchronize")

        self.dlg_parse_settings(['SYNC_SETTINGS'])

        check_ok, check_log = self.sys_check_settings(['SYNC_SETTINGS'])
        process_log += check_log

        if check_ok:
            sync_source_layer = self.tool_get_sync_source_layer()
            process_log.append(f"{tab}✓ Source-Layer '{sync_source_layer.name()}'")
            sync_target_layer = self.tool_get_sync_target_layer()
            process_log.append(f"{tab}✓ Target-Layer '{sync_target_layer.name()}'")

            debug_log(sync_source_layer is sync_target_layer)

            if not sync_source_layer is sync_target_layer:

                if sync_target_layer.isEditable():
                    num_features = sync_source_layer.featureCount()
                    if num_features:
                        sync_target_dir_posix = Path(self.stored_settings.sync_target_dir)
                        process_log.append(f"{tab}✓ sync_target_dir '{sync_target_dir_posix.as_posix()}'")
                        process_log.append(f"{tab}✓ sync_file_mode '{self.stored_settings.sync_file_mode}'")
                        process_log.append(f"{tab}✓ {sync_source_layer.featureCount()} num features")
                        tr_source_2_target = qgis._core.QgsCoordinateTransform(sync_source_layer.crs(), sync_target_layer.crs(), qgis._core.QgsProject.instance())

                        self.my_dialog.sub_wdg_file_sync_progress.setVisible(True)
                        self.my_dialog.qprb_file_sync.setMinimum(0)
                        self.my_dialog.qprb_file_sync.setMaximum(num_features)
                        self.my_dialog.qprb_file_sync.setValue(0)
                        self.my_dialog.qlbl_file_sync_progress.setText('')

                        process_log.append(f"{tab}Feature-Iteration-Start")
                        fc = 0
                        success_fids = []
                        insert_fids = []
                        update_fids = []
                        duplicate_fids = []
                        error_fids = []

                        missing_files = []
                        error_files = []
                        copied_files = []
                        existing_files_kept = []
                        existing_files_skipped = []
                        existing_files_replaced = []
                        existing_files_renamed = []
                        for sync_source_feature in sync_source_layer.getFeatures():
                            fc += 1
                            self.my_dialog.qprb_file_sync.setValue(fc)
                            self.my_dialog.qlbl_file_sync_progress.setText(f"Feature {fc} from {num_features}")

                            sync_source_path_str = sync_source_feature[self.stored_settings.sync_source_abs_path_field]

                            sync_source_path_posix = Path(sync_source_path_str)

                            process_log.append(f"{tab}{tab} #{sync_source_feature.id()} '{sync_source_path_posix}'")

                            if sync_source_path_posix.is_file():

                                process_log.append(f"{tab}{tab}{tab}✔ source-file exists")

                                sync_target_path_posix = None

                                if self.stored_settings.sync_file_mode == 'keep':
                                    sync_target_path_posix = sync_source_path_posix
                                # keep or copy file?
                                if self.stored_settings.sync_file_mode == 'copy':

                                    # sync_target_dir_posix checked before
                                    composed_target_dir_posix = sync_target_dir_posix

                                    # optionally use sub-directory from source-layer-field
                                    if self.stored_settings.sync_source_rel_path_field:
                                        sync_source_rel_path_str = sync_source_feature[self.stored_settings.sync_source_rel_path_field]
                                        if sync_source_rel_path_str:
                                            composed_target_dir_posix = sync_target_dir_posix / sync_source_rel_path_str

                                    # sync_target_dir check, exists, isdir/isfile, or create
                                    if composed_target_dir_posix.is_dir():
                                        # idealfall: Verzeichnis ist bereits vorhanden
                                        pass
                                    elif composed_target_dir_posix.is_file():
                                        # bereits vorhanden, aber ist eine Datei => geht nicht!
                                        process_log.append(f"<b>{tab}{tab}{tab}⭍ Target-directory '{composed_target_dir_posix}' is a file, file skipped</b>")
                                        error_fids.append(sync_source_feature.id())
                                        error_files.append(sync_source_path_posix)
                                        continue
                                    else:
                                        # noch nicht vorhanden => anlegen, makedirs => rekursiv
                                        try:
                                            composed_target_dir_posix.mkdir(parents=True)
                                        except:
                                            process_log.append(f"<b>{tab}{tab}{tab}⭍ Target-directory '{composed_target_dir_posix}' could not be created, file skipped</b>")
                                            error_fids.append(sync_source_feature.id())
                                            error_files.append(sync_source_path_posix)
                                            continue

                                    prelim_target_path_posix = composed_target_dir_posix / sync_source_path_posix.name

                                    # check

                                    if prelim_target_path_posix.is_dir():
                                        # bereits vorhanden, aber ist ein Verzeichnis => geht nicht!
                                        process_log.append(f"<b>{tab}{tab}{tab}⭍ Target-path '{prelim_target_path_posix}' is a directory, file skipped</b>")
                                        error_fids.append(sync_source_feature.id())
                                        error_files.append(sync_source_path_posix)
                                        continue


                                    elif prelim_target_path_posix.is_file():
                                        copy_target_path_posix = None
                                        if self.stored_settings.sync_existing_file_mode == 'skip':
                                            process_log.append(f"{tab}{tab}{tab}existing target-file kept")
                                            sync_target_path_posix = prelim_target_path_posix
                                            existing_files_kept.append(sync_source_path_posix)
                                        elif self.stored_settings.sync_existing_file_mode == 'replace':
                                            process_log.append(f"{tab}{tab}{tab}existing target-file replaced")
                                            copy_target_path_posix = prelim_target_path_posix
                                            existing_files_replaced.append(sync_source_path_posix)
                                        elif self.stored_settings.sync_existing_file_mode == 'rename':
                                            renamed_path_posix = MyTools.create_unique_file_path(prelim_target_path_posix)
                                            process_log.append(f"{tab}{tab}{tab}existing target-file, source-file renamed")
                                            copy_target_path_posix = renamed_path_posix
                                            existing_files_renamed.append(sync_source_path_posix)
                                        else:
                                            # sollte eigentlich nicht vorkommen
                                            process_log.append(f"{tab}{tab}{tab}target-file already exists, skip file and sync...")
                                            existing_files_skipped.append(sync_source_path_posix)
                                            continue
                                    else:
                                        # file with this path not found
                                        copy_target_path_posix = prelim_target_path_posix
                                        process_log.append(f"{tab}{tab}{tab}no target-file found, copy source-file")
                                        copied_files.append(sync_source_path_posix)

                                    if copy_target_path_posix:
                                        # https://docs.python.org/3/library/shutil.html
                                        # Copy/rename the file
                                        # copy2 => permissions and metadata are preserved
                                        try:
                                            shutil.copy2(sync_source_path_posix, copy_target_path_posix)
                                            process_log.append(f"{tab}{tab}{tab}✔ target-file stored as '{copy_target_path_posix}'...")
                                            sync_target_path_posix = copy_target_path_posix
                                        except:
                                            process_log.append(f"<b>{tab}{tab}{tab}⭍ target-file storage as '{copy_target_path_posix}' failed, skip file and sync.../b>")
                                            error_fids.append(sync_source_feature.id())
                                            error_files.append(sync_source_path_posix)
                                            continue

                                if sync_target_path_posix:
                                    insert_features = []
                                    update_overwrite_features = []
                                    update_preserve_features = []

                                    duplicate_features = list(MyTools.get_features_by_value(sync_target_layer, self.stored_settings.sync_target_abs_path_field, sync_target_path_posix.as_posix()))

                                    if duplicate_features:
                                        if self.stored_settings.sync_existing_feature_mode == 'skip':
                                            process_log.append(f"{tab}{tab}{tab}{len(duplicate_features)} feature(s) with duplicate path found, feature skipped")
                                            duplicate_fids.append(sync_source_feature.id())
                                        elif self.stored_settings.sync_existing_feature_mode == 'replace':
                                            process_log.append(f"{tab}{tab}{tab}{len(duplicate_features)} feature(s) with duplicate path found, features deleted and new feature inserted")
                                            for duplicate_feature in duplicate_features:
                                                sync_target_layer.deleteFeature(duplicate_feature.id())
                                            sync_target_feature = qgis._core.QgsFeature(sync_target_layer.dataProvider().fields())
                                            insert_features.append(sync_target_feature)
                                        elif self.stored_settings.sync_existing_feature_mode == 'insert':
                                            process_log.append(f"{tab}{tab}{tab}{len(duplicate_features)} feature(s) with duplicate path found, insert new duplicate")
                                            sync_target_feature = qgis._core.QgsFeature(sync_target_layer.dataProvider().fields())
                                            insert_features.append(sync_target_feature)
                                        elif self.stored_settings.sync_existing_feature_mode == 'update_overwrite':
                                            process_log.append(f"{tab}{tab}{tab}{len(duplicate_features)} feature(s) with duplicate path found, update duplicate(s) replacing existing attributes")
                                            update_overwrite_features = duplicate_features
                                        elif self.stored_settings.sync_existing_feature_mode == 'update_preserve':
                                            process_log.append(f"{tab}{tab}{tab}{len(duplicate_features)} feature(s) with duplicate path found, update duplicate(s) keeping existing attributes")
                                            update_preserve_features = duplicate_features
                                    else:
                                        sync_target_feature = qgis._core.QgsFeature(sync_target_layer.dataProvider().fields())
                                        insert_features.append(sync_target_feature)

                                    source_geom = None
                                    if sync_source_feature.hasGeometry():
                                        source_geom = sync_source_feature.geometry()
                                        source_geom.transform(tr_source_2_target)

                                    for insert_feature in insert_features:

                                        if source_geom:
                                            insert_feature.setGeometry(source_geom)

                                        insert_feature[self.stored_settings.sync_target_abs_path_field] = sync_target_path_posix.as_posix()

                                        for sync_target_field_name, sync_source_field_name in self.stored_settings.sync_fields.items():
                                            insert_feature[sync_target_field_name] = sync_source_feature[sync_source_field_name]

                                        sync_target_layer.addFeature(insert_feature)

                                        process_log.append(f"{tab}{tab}{tab}{tab}✔ insert successful")
                                        insert_fids.append(sync_source_feature.id())

                                    for update_overwrite_feature in update_overwrite_features:
                                        if source_geom and self.stored_settings.sync_update_geometries:
                                            update_overwrite_feature.setGeometry(source_geom)
                                            process_log.append(f"{tab}{tab}{tab}{tab}✔ setGeometry successful")

                                        update_overwrite_feature[self.stored_settings.sync_target_abs_path_field] = sync_target_path_posix.as_posix()

                                        for sync_target_field_name, sync_source_field_name in self.stored_settings.sync_fields.items():
                                            update_overwrite_feature[sync_target_field_name] = sync_source_feature[sync_source_field_name]

                                        sync_target_layer.updateFeature(update_overwrite_feature)

                                        process_log.append(f"{tab}{tab}{tab}{tab}✔ update_overwrite successful")
                                        update_fids.append(sync_source_feature.id())

                                    for update_preserve_feature in update_preserve_features:
                                        feature_changed = False
                                        if source_geom and self.stored_settings.sync_update_geometries and not update_preserve_feature.hasGeometry():
                                            update_preserve_feature.setGeometry(source_geom)
                                            process_log.append(f"{tab}{tab}{tab}{tab}✔ setGeometry successful")
                                            feature_changed = True

                                        if update_preserve_feature[self.stored_settings.sync_target_abs_path_field] != sync_target_path_posix.as_posix():
                                            update_preserve_feature[self.stored_settings.sync_target_abs_path_field] = sync_target_path_posix.as_posix()
                                            feature_changed = True

                                        for sync_target_field_name, sync_source_field_name in self.stored_settings.sync_fields.items():

                                            if update_preserve_feature[sync_target_field_name] in [qgis.core.NULL, None, ''] and sync_source_feature[sync_source_field_name] not in [qgis.core.NULL, None, ''] and update_preserve_feature[sync_target_field_name] != sync_source_feature[sync_source_field_name]:
                                                update_preserve_feature[sync_target_field_name] = sync_source_feature[sync_source_field_name]
                                                feature_changed = True

                                        if feature_changed:
                                            sync_target_layer.updateFeature(update_preserve_feature)
                                            process_log.append(f"{tab}{tab}{tab}{tab}✔ update_preserve successful")
                                            update_fids.append(sync_source_feature.id())
                                        else:
                                            duplicate_fids.append(sync_source_feature.id())



                            else:
                                error_fids.append(sync_source_feature.id())
                                process_log.append(f"<b>{tab}{tab}{tab}⭍ file not found, skip...</b>")
                                missing_files.append(sync_source_path_posix)
                                continue

                        process_log.append(f"{tab}...Feature-Iteration-End")
                        process_log.append(f"{tab}{len(copied_files)} files copied")
                        process_log.append(f"{tab}{len(existing_files_kept)} files kept in place")
                        process_log.append(f"{tab}{len(existing_files_skipped)} existing files skipped")
                        process_log.append(f"{tab}{len(existing_files_replaced)} existing files replaced")
                        process_log.append(f"{tab}{len(insert_fids)} features inserted")
                        process_log.append(f"{tab}{len(update_fids)} features updated")
                        process_log.append(f"{tab}{len(duplicate_fids)} duplicate features skipped")
                        process_log.append(f"{tab}{len(error_fids)} features with errors skipped and selected")

                        sync_source_layer.selectByIds(error_fids)
                    else:
                        process_log.append(f"<b>{tab}⭍ no features in Source-Layer...</b>")
                else:
                    process_log.append(f"<b>{tab}⭍ Target-Layer not editable...</b>")
            else:
                process_log.append(f"<b>{tab}⭍ Source- and Target-Layer identical...</b>")
        else:
            process_log.append(f"<b>{tab}⭍ Settings invalid...</b>")

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} end synchronize, runtime {(time.perf_counter_ns() - t_1) * 1e-9:.5f} s")
        self.tool_append_to_log_history(process_log)

    def tool_get_sync_source_field(self, sync_source_field_name):
        """wrapper to get field by name from sync_source_layer"""
        # Rev. 2025-06-11
        sync_source_layer = self.tool_get_sync_source_layer()
        if sync_source_layer:
            fnx = sync_source_layer.fields().indexOf(sync_source_field_name)
            if fnx >= 0:
                return sync_source_layer.fields()[fnx]

        return None

    def tool_get_post_scan_field(self, post_scan_field_name):
        """wrapper to get field by name from post_scan_layer"""
        # Rev. 2025-06-11
        post_scan_layer = self.tool_get_post_scan_layer()
        if post_scan_layer:
            fnx = post_scan_layer.fields().indexOf(post_scan_field_name)
            if fnx >= 0:
                return post_scan_layer.fields()[fnx]
        return None

    def tool_get_sync_source_layer(self) -> qgis._core.QgsVectorLayer:
        """wrapper to get and check sync_source_layer by self.stored_settings.sync_source_layer_id"""
        # Rev. 2025-06-11
        point_wkb_types = [
            qgis._core.QgsWkbTypes.Point,
            qgis._core.QgsWkbTypes.PointZ,
            qgis._core.QgsWkbTypes.PointM,
            qgis._core.QgsWkbTypes.PointZM,
        ]
        #  and sync_source_layer.dataProvider().wkbType() in point_wkb_types
        if self.stored_settings.sync_source_layer_id:
            sync_source_layer = qgis._core.QgsProject.instance().mapLayer(self.stored_settings.sync_source_layer_id)
            if (sync_source_layer and sync_source_layer.isValid() and sync_source_layer.type() == qgis._core.Qgis.LayerType.VectorLayer):
                return sync_source_layer

    def tool_get_sync_target_layer(self) -> qgis._core.QgsVectorLayer:
        """wrapper to get and check sync_target_layer by self.stored_settings.sync_target_layer_id"""
        # Rev. 2025-06-11
        point_wkb_types = [
            qgis._core.QgsWkbTypes.Point,
            qgis._core.QgsWkbTypes.PointZ,
            qgis._core.QgsWkbTypes.PointM,
            qgis._core.QgsWkbTypes.PointZM,
        ]

        # and sync_target_layer.dataProvider().wkbType() in point_wkb_types
        if self.stored_settings.sync_target_layer_id:
            sync_target_layer = qgis._core.QgsProject.instance().mapLayer(self.stored_settings.sync_target_layer_id)
            if (sync_target_layer and sync_target_layer.isValid() and sync_target_layer.type() == qgis._core.Qgis.LayerType.VectorLayer and sync_target_layer.dataProvider().name() != 'virtual'):
                return sync_target_layer

    def tool_get_post_scan_layer(self) -> qgis._core.QgsVectorLayer:
        """wrapper to get and check post_scan_layer by self.stored_settings.post_scan_layer_id"""
        # Rev. 2025-06-11

        # point_wkb_types = [
        #     qgis._core.QgsWkbTypes.Point,
        #     qgis._core.QgsWkbTypes.PointZ,
        #     qgis._core.QgsWkbTypes.PointM,
        #     qgis._core.QgsWkbTypes.PointZM,
        # ]
        # sync_target_layer.dataProvider().wkbType() in point_wkb_types and
        if self.stored_settings.post_scan_layer_id:
            post_scan_layer = qgis._core.QgsProject.instance().mapLayer(self.stored_settings.post_scan_layer_id)
            # new: any vectorlayer with absolute_path-field independend from GeometryType
            if (post_scan_layer and post_scan_layer.isValid() and post_scan_layer.type() == qgis._core.Qgis.LayerType.VectorLayer and post_scan_layer.dataProvider().name() != 'virtual'):
                return post_scan_layer

    def tool_get_sync_target_field(self, sync_target_field_name):
        """wrapper to get field by name from sync_target_layer"""
        # Rev. 2025-06-11
        sync_target_layer = self.tool_get_sync_target_layer()
        if sync_target_layer:
            fnx = sync_target_layer.fields().indexOf(sync_target_field_name)
            if fnx >= 0:
                return sync_target_layer.fields()[fnx]
            # else:
            # self.iface.messageBar().pushMessage("FileSync", f"sync-target-field '{sync_target_field_name}' not found in '{sync_target_layer.name()}'", level=qgis._core.Qgis.Info, duration=5)
            # pass
        # else:
        # pass

        return None

    def dlg_add_sync_mapping(self):
        """checks and adds a source-field to target-field mapping to self.stored_settings.sync_fields"""
        # Rev. 2025-06-11
        int_types = [
            QtCore.QVariant.Int,
            QtCore.QVariant.LongLong,
            QtCore.QVariant.UInt,
            QtCore.QVariant.ULongLong,
        ]
        if self.my_dialog.qlw_sync_source_layer_fields.selectedItems():
            source_qlwi = self.my_dialog.qlw_sync_source_layer_fields.selectedItems()[0]
            sync_source_field_name = source_qlwi.data(QtCore.Qt.DisplayRole)
            sync_source_field = self.tool_get_sync_source_field(sync_source_field_name)

            if sync_source_field:

                if self.my_dialog.qlw_sync_target_layer_fields.selectedItems():
                    target_qlwi = self.my_dialog.qlw_sync_target_layer_fields.selectedItems()[0]
                    sync_target_field_name = target_qlwi.data(QtCore.Qt.DisplayRole)
                    sync_target_field = self.tool_get_sync_target_field(sync_target_field_name)

                    if sync_target_field:
                        if sync_source_field.type() == sync_target_field.type() or (sync_source_field.type() in int_types and sync_target_field.type() in int_types):
                            # check for duplicates
                            if sync_target_field_name in [self.stored_settings.sync_target_abs_path_field]:
                                self.iface.messageBar().pushMessage("FileSync", f"Target-Field '{sync_target_field_name}' already registered as sync_target_abs_path_field", level=qgis._core.Qgis.Info, duration=5)
                            elif sync_target_field_name in self.stored_settings.sync_fields:
                                self.iface.messageBar().pushMessage("FileSync", f"Target-Field '{sync_target_field_name}' already registered", level=qgis._core.Qgis.Info, duration=5)
                            else:
                                self.stored_settings.sync_fields[sync_target_field_name] = sync_source_field_name
                                self.dlg_refresh_qtw_sync_mappings()

                            self.dlg_refresh_sync_target_fields()
                        else:
                            # should never happen, because not matching field-types will be disabled in qlw_sync_target_layer_fields
                            self.iface.messageBar().pushMessage("FileSync", f"Selected source- and target-field have different field-types...", level=qgis._core.Qgis.Info, duration=5)
            else:
                self.iface.messageBar().pushMessage("FileSync", f"Select matching source- and target-field!", level=qgis._core.Qgis.Info, duration=5)
        else:
            self.iface.messageBar().pushMessage("FileSync", f"Select matching source- and target-field!", level=qgis._core.Qgis.Info, duration=5)

    def scc_clear_sync_mappings(self):
        """resets self.stored_settings.sync_fields"""
        # Rev. 2025-06-11
        self.my_dialog.qtw_sync_mappings.setRowCount(0)
        self.stored_settings.sync_fields = {}

    def dlg_qtw_sync_mappings_clicked(self, item):
        """click-signal in self.my_dialog.qtw_sync_mappings
        if registered in last column ("✖"): delete mapping from self.stored_settings.sync_fields and refreshes qtw_sync_mappings"""
        # Rev. 2025-06-11
        if item.column() == 3:
            target_qlwi = self.my_dialog.qtw_sync_mappings.item(item.row(), 2)
            sync_target_field_name = target_qlwi.data(QtCore.Qt.DisplayRole)
            self.stored_settings.sync_fields.pop(sync_target_field_name, None)
            self.dlg_refresh_qtw_sync_mappings()

    def dlg_source_layer_fields_selection_changed(self):
        """source-field in qlw_sync_source_layer_fields selected => show mappable target fields in qlw_sync_target_layer_fields"""
        # Rev. 2025-06-11

        int_types = [
            QtCore.QVariant.Int,
            QtCore.QVariant.LongLong,
            QtCore.QVariant.UInt,
            QtCore.QVariant.ULongLong,
        ]

        # selectedItems will be empty, if selection was cleared with mit strg + click
        if self.my_dialog.qlw_sync_source_layer_fields.selectedItems():
            source_qlwi = self.my_dialog.qlw_sync_source_layer_fields.selectedItems()[0]
            sync_source_field_name = source_qlwi.data(QtCore.Qt.DisplayRole)
            sync_source_field = self.tool_get_sync_source_field(sync_source_field_name)

            if sync_source_field:
                default_flag = QtCore.Qt.ItemFlags(53)
                not_selectable_flag = QtCore.Qt.ItemFlags(21)
                for rc in range(self.my_dialog.qlw_sync_target_layer_fields.model().rowCount()):
                    target_qlwi = self.my_dialog.qlw_sync_target_layer_fields.item(rc)
                    sync_target_field_name = target_qlwi.data(QtCore.Qt.DisplayRole)
                    sync_target_field = self.tool_get_sync_target_field(sync_target_field_name)
                    if sync_target_field:
                        # disable already assigned fields
                        if sync_target_field.name() in [self.stored_settings.sync_target_abs_path_field] or sync_target_field.name() in self.stored_settings.sync_fields:
                            # not_selectable_flag
                            target_qlwi.setFlags(not_selectable_flag)
                            target_qlwi.setSelected(False)

                        # disable not matching field-types
                        elif not (sync_source_field.type() == sync_target_field.type() or (sync_source_field.type() in int_types and sync_target_field.type() in int_types)):
                            target_qlwi.setFlags(not_selectable_flag)
                            target_qlwi.setSelected(False)
                        else:
                            # enable the rest and conveniently select if the field-names match
                            target_qlwi.setFlags(default_flag)
                            if sync_source_field_name == sync_target_field_name:
                                target_qlwi.setSelected(True)

                    else:
                        # target-field not found => refresh self.my_dialog.qlw_sync_target_layer_fields
                        self.dlg_refresh_sync_target_fields()
            else:
                # source-field not found => refresh self.my_dialog.qlw_sync_source_layer_fields
                self.dlg_refresh_sync_source_fields()

    def s_open_sync_source_table(self):
        """show sync_source_layer-table"""
        # Rev. 2025-06-11
        sync_source_layer = self.tool_get_sync_source_layer()

        if sync_source_layer:
            MyTools.re_open_attribute_tables(self.iface, sync_source_layer, True)
        else:
            self.iface.messageBar().pushMessage("FileSync", "no sync_source_layer", level=qgis._core.Qgis.Info, duration=5)

    def s_open_sync_target_table(self):
        """show sync_target_layer-table"""
        # Rev. 2025-06-11
        sync_target_layer = self.tool_get_sync_target_layer()
        if sync_target_layer:
            MyTools.re_open_attribute_tables(self.iface, sync_target_layer, True)
        else:
            self.iface.messageBar().pushMessage("FileSync", "no sync_target_layer", level=qgis._core.Qgis.Info, duration=5)

    def s_open_post_scan_layer(self):
        """show post_scan_layer-table"""
        # Rev. 2025-06-11
        post_scan_layer = self.my_dialog.qcbn_post_scan_layer.currentData(Qt_Roles.RETURN_VALUE)
        if post_scan_layer:
            MyTools.re_open_attribute_tables(self.iface, post_scan_layer, True)

    def scc_select_sync_source_lyr(self):
        """sets self.stored_settings.sync_source_layer_id and refreshes field-selectors"""
        # Rev. 2025-06-11
        self.stored_settings.sync_source_layer_id = ''
        selected_sync_lyr = self.my_dialog.qcbn_sync_source_layer.currentData(Qt_Roles.RETURN_VALUE)
        if selected_sync_lyr:
            self.stored_settings.sync_source_layer_id = selected_sync_lyr.id()

        self.dlg_refresh_sync_source_fields()

    def dlg_refresh_sync_source_fields(self):
        """if sync_source_layer changes:
        populate self.my_dialog.qlw_sync_source_layer_fields, self.my_dialog.qcb_sync_source_abs_path_field and self.my_dialog.qcb_sync_source_rel_path_field"""
        # Rev. 2025-06-11
        if self.my_dialog:
            string_types = [
                QtCore.QVariant.String,
                QtCore.QMetaType.QString,
            ]

            double_types = [
                QtCore.QVariant.Double,
                QtCore.QMetaType.Double
            ]

            self.my_dialog.qlw_sync_source_layer_fields.blockSignals(True)
            self.my_dialog.qcb_sync_source_abs_path_field.blockSignals(True)
            self.my_dialog.qcb_sync_source_rel_path_field.blockSignals(True)

            self.my_dialog.qlw_sync_source_layer_fields.clear()
            self.my_dialog.qcb_sync_source_abs_path_field.clear()
            self.my_dialog.qcb_sync_source_abs_path_field.addItem('')
            self.my_dialog.qcb_sync_source_rel_path_field.clear()
            self.my_dialog.qcb_sync_source_rel_path_field.addItem('')
            sync_source_layer = self.tool_get_sync_source_layer()
            if sync_source_layer:
                f_idx = 0
                pk_idcs = sync_source_layer.primaryKeyAttributes()
                # not only dataProvider()-fields to include calculated fields
                for field in sync_source_layer.fields():
                    qlwi = QtWidgets.QListWidgetItem()
                    qlwi.setText(field.name())

                    ttp = f"Source-Field\nName: {field.name()}\nIndex: {f_idx}\nType: '{field.friendlyTypeString()}'\nPK-Field: {f_idx in pk_idcs}\nVirtual: {field not in sync_source_layer.dataProvider().fields()}"
                    qlwi.setData(QtCore.Qt.ToolTipRole, ttp)
                    # restriction only necessary for target-layer
                    self.my_dialog.qlw_sync_source_layer_fields.addItem(qlwi)

                    if field.type() in string_types:
                        self.my_dialog.qcb_sync_source_abs_path_field.addItem(field.name(), field)
                        self.my_dialog.qcb_sync_source_rel_path_field.addItem(field.name(), field)

                    f_idx += 1

            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_source_abs_path_field, self.stored_settings.sync_source_abs_path_field)
            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_source_rel_path_field, self.stored_settings.sync_source_rel_path_field)

            self.my_dialog.qlw_sync_source_layer_fields.blockSignals(False)
            self.my_dialog.qcb_sync_source_abs_path_field.blockSignals(False)
            self.my_dialog.qcb_sync_source_rel_path_field.blockSignals(False)

    def dlg_refresh_qtw_sync_mappings(self):
        """shows self.stored_settings.sync_fields in self.my_dialog.qtw_sync_mappings"""
        # Rev. 2025-06-11
        if self.my_dialog:
            int_types = [
                QtCore.QVariant.Int,
                QtCore.QVariant.LongLong,
                QtCore.QVariant.UInt,
                QtCore.QVariant.ULongLong,
            ]
            is_enabled_flag = QtCore.Qt.ItemFlags(32)
            sync_source_layer = self.tool_get_sync_source_layer()
            sync_target_layer = self.tool_get_sync_target_layer()

            self.dlg_resize_sync_cols()

            self.my_dialog.qtw_sync_mappings.setRowCount(0)

            if sync_source_layer and sync_target_layer:
                for sync_target_field_name, sync_source_field_name in self.stored_settings.sync_fields.items():
                    sync_target_field = self.tool_get_sync_target_field(sync_target_field_name)
                    sync_source_field = self.tool_get_sync_source_field(sync_source_field_name)
                    if sync_target_field and sync_source_field and (sync_target_field.type() == sync_source_field.type() or (sync_source_field.type() in int_types and sync_target_field.type() in int_types)):
                        rc = self.my_dialog.qtw_sync_mappings.rowCount()
                        self.my_dialog.qtw_sync_mappings.insertRow(rc)

                        source_qtwi = QtWidgets.QTableWidgetItem(sync_source_field_name)
                        source_qtwi.setFlags(is_enabled_flag)
                        ttp = f"Source-Field\nName: {sync_source_field_name}\nType: '{sync_source_field.friendlyTypeString()}'"
                        source_qtwi.setData(QtCore.Qt.ToolTipRole, ttp)
                        self.my_dialog.qtw_sync_mappings.setItem(rc, 0, source_qtwi)

                        arrow_qtwi = QtWidgets.QTableWidgetItem("➜")
                        arrow_qtwi.setFlags(is_enabled_flag)
                        self.my_dialog.qtw_sync_mappings.setItem(rc, 1, arrow_qtwi)

                        target_qtwi = QtWidgets.QTableWidgetItem(sync_target_field_name)
                        target_qtwi.setFlags(is_enabled_flag)
                        ttp = f"Target-Field\nName: {sync_target_field_name}\nType: '{sync_target_field.friendlyTypeString()}'"
                        target_qtwi.setData(QtCore.Qt.ToolTipRole, ttp)
                        self.my_dialog.qtw_sync_mappings.setItem(rc, 2, target_qtwi)

                        delete_qtwi = QtWidgets.QTableWidgetItem("✖")
                        delete_qtwi.setToolTip("remove mapping")
                        delete_qtwi.setFlags(is_enabled_flag)
                        self.my_dialog.qtw_sync_mappings.setItem(rc, 3, delete_qtwi)
                    else:
                        # fields do not match anymore, field-type must have changed somehow
                        del self.stored_settings.sync_fields[sync_target_field_name]

    def dlg_refresh_post_scan_layer_fields(self):
        """refreshes self.my_dialog.qcb_post_scan_abs_path_field after change of post_scan_layer"""
        # Rev. 2025-06-11

        string_types = [
            QtCore.QVariant.String,
            QtCore.QMetaType.QString,
        ]
        self.my_dialog.qcb_post_scan_abs_path_field.blockSignals(True)

        self.my_dialog.qcb_post_scan_abs_path_field.clear()
        self.my_dialog.qcb_post_scan_abs_path_field.addItem('')

        post_scan_layer = self.tool_get_post_scan_layer()
        if post_scan_layer:
            for field in post_scan_layer.dataProvider().fields():
                if field.type() in string_types:
                    self.my_dialog.qcb_post_scan_abs_path_field.addItem(field.name(), field)

            MyTools.qcbx_select_by_value(self.my_dialog.qcb_post_scan_abs_path_field, self.stored_settings.post_scan_abs_path_field)

        self.my_dialog.qcb_post_scan_abs_path_field.blockSignals(False)

    def dlg_refresh_sync_target_fields(self):
        """refreshes qlw_sync_target_layer_fields and qcb_sync_target_abs_path_field after change of sync_target_layer"""
        # Rev. 2025-06-11
        if self.my_dialog:
            string_types = [
                QtCore.QVariant.String,
                QtCore.QMetaType.QString,
            ]

            double_types = [
                QtCore.QVariant.Double,
                QtCore.QMetaType.Double
            ]
            self.my_dialog.qlw_sync_target_layer_fields.blockSignals(True)
            self.my_dialog.qcb_sync_target_abs_path_field.blockSignals(True)

            self.my_dialog.qlw_sync_target_layer_fields.clear()
            self.my_dialog.qcb_sync_target_abs_path_field.clear()
            self.my_dialog.qcb_sync_target_abs_path_field.addItem('')
            sync_target_layer = self.tool_get_sync_target_layer()
            not_selectable_flag = QtCore.Qt.ItemFlags(21)
            if sync_target_layer:
                f_idx = 0
                pk_idcs = sync_target_layer.primaryKeyAttributes()
                # not only dataProvider()-fields to include calculated fields
                for field in sync_target_layer.dataProvider().fields():
                    qlwi = QtWidgets.QListWidgetItem()
                    qlwi.setText(field.name())

                    ttp = f"Target-Field\nName: {field.name()}\nIndex: {f_idx}\nType: '{field.friendlyTypeString()}'\nPK-Field: {f_idx in pk_idcs}\nVirtual: {field not in sync_target_layer.dataProvider().fields()}"

                    # restriction for already assigned "special"-fields
                    if field.name() == self.stored_settings.sync_target_abs_path_field:
                        qlwi.setFlags(not_selectable_flag)
                        qlwi.setSelected(False)
                        ttp += "\nalready registered as Path-Field"
                    elif field.name() in self.stored_settings.sync_fields:
                        qlwi.setFlags(not_selectable_flag)
                        qlwi.setSelected(False)
                        ttp += "\nalready registered as Sync-Field"

                    qlwi.setData(QtCore.Qt.ToolTipRole, ttp)

                    self.my_dialog.qlw_sync_target_layer_fields.addItem(qlwi)

                    if field.type() in string_types:
                        self.my_dialog.qcb_sync_target_abs_path_field.addItem(field.name(), field)

                    f_idx += 1

            MyTools.qcbx_select_by_value(self.my_dialog.qcb_sync_target_abs_path_field, self.stored_settings.sync_target_abs_path_field)

            self.my_dialog.qlw_sync_target_layer_fields.blockSignals(False)
            self.my_dialog.qcb_sync_target_abs_path_field.blockSignals(False)

    def scc_select_sync_target_lyr(self):
        """parses sync_target_layer_id from self.my_dialog.qcbn_sync_target_layer"""
        # Rev. 2025-06-11
        self.stored_settings.sync_target_layer_id = ''
        selected_sync_lyr = self.my_dialog.qcbn_sync_target_layer.currentData(Qt_Roles.RETURN_VALUE)
        if selected_sync_lyr:
            self.stored_settings.sync_target_layer_id = selected_sync_lyr.id()

        self.dlg_refresh_sync_target_fields()

    def dlg_refresh_sync_layers(self):
        """refreshes and selects two QListWidgets used to select Sync-Layer"""
        # Rev. 2025-06-11
        if self.my_dialog:
            self.my_dialog.qlw_sync_source_layer_fields.clear()
            self.my_dialog.qlw_sync_target_layer_fields.clear()
            enable_criteria = {
                # 'data_provider': ['ogr'],
                # 'geometry_type': [qgis._core.Qgis.GeometryType.Point]
                'layer_type': [0]
            }

            self.my_dialog.qcbn_sync_source_layer.load_data(enable_criteria)
            self.my_dialog.qcbn_sync_source_layer.setEnabled(True)

            sync_source_layer = self.tool_get_sync_source_layer()
            if sync_source_layer:
                self.my_dialog.qcbn_sync_source_layer.select_by_value([[0, Qt_Roles.RETURN_VALUE, QtCore.Qt.MatchExactly]], sync_source_layer, True)
                self.dlg_refresh_sync_source_fields()

            enable_criteria = {
                # 'data_provider': ['ogr'],
                # 'geometry_type': [qgis._core.Qgis.GeometryType.Point]
                'layer_type': [0]
            }

            self.my_dialog.qcbn_sync_target_layer.load_data(enable_criteria)
            self.my_dialog.qcbn_sync_target_layer.setEnabled(True)

            sync_target_layer = self.tool_get_sync_target_layer()
            if sync_target_layer:
                self.my_dialog.qcbn_sync_target_layer.select_by_value([[0, Qt_Roles.RETURN_VALUE, QtCore.Qt.MatchExactly]], sync_target_layer, True)
                self.dlg_refresh_sync_target_fields()

    def dlg_refresh_post_scan_layers(self):
        """refreshes list of selectable post_scan_layers"""
        # Rev. 2025-06-11
        if self.my_dialog:
            enable_criteria = {
                # only vector-layer
                'layer_type': [0],
            }

            self.my_dialog.qcbn_post_scan_layer.load_data(enable_criteria)

            post_scan_layer = self.tool_get_post_scan_layer()
            if post_scan_layer:
                self.my_dialog.qcbn_post_scan_layer.select_by_value([[0, Qt_Roles.RETURN_VALUE, QtCore.Qt.MatchExactly]], post_scan_layer, True)

    def dlg_refresh_layer_action_layers(self):
        """refreshes list of selectable layer-action-layers"""
        # Rev. 2025-06-11
        if self.my_dialog:
            self.my_dialog.qcbx_layer_action_abs_path_field.clear()
            self.my_dialog.qcbx_layer_action_direction_field.clear()
            self.my_dialog.qcbx_layer_action_last_edit_date_time_field.clear()

            enable_criteria = {
                # only vector-layer
                'layer_type': [0],
            }

            self.my_dialog.qcbn_layer_action_layer.load_data(enable_criteria)

    def scc_select_pre_scan_patterns(self):
        """called from self.my_dialog.qcb_select_pre_scan_patterns.currentIndexChanged"""
        # Rev. 2025-06-11
        pre_scan_patterns = self.my_dialog.qcb_select_pre_scan_patterns.currentText()
        self.my_dialog.qle_pre_scan_patterns.setText(pre_scan_patterns)
        self.stored_settings.pre_scan_patterns = pre_scan_patterns

    def scc_select_sync_existing_file_mode(self):
        """called from self.my_dialog.qcb_sync_existing_file_mode.currentIndexChanged"""
        # Rev. 2025-06-11
        self.stored_settings.sync_existing_file_mode = self.my_dialog.qcb_sync_existing_file_mode.currentData()

    def scc_select_sync_existing_feature_mode(self):
        """called from self.my_dialog.qcb_sync_existing_feature_mode.currentIndexChanged"""
        # Rev. 2025-06-11
        self.stored_settings.sync_existing_feature_mode = self.my_dialog.qcb_sync_existing_feature_mode.currentData()

    def dlg_parse_settings(self, use_cases=None) -> tuple:
        """parse settings from dialog (additional to some single-widget-parsers)
        :param use_cases: if None, all three dialog-tabs are parsed
        :returns: tuple(check_ok,process_log)"""
        # Rev. 2025-06-11
        if not use_cases:
            use_cases = ['PRE_SCAN_SETTINGS', 'SYNC_SETTINGS', 'POST_SCAN_SETTINGS']

        if self.my_dialog:
            if 'PRE_SCAN_SETTINGS' in use_cases:

                pre_scan_dir = self.my_dialog.qle_pre_scan_dir.text()
                if pre_scan_dir:
                    self.stored_settings.pre_scan_dir = pre_scan_dir
                else:
                    self.stored_settings.pre_scan_dir = os.path.expanduser('~')
                    self.my_dialog.qle_pre_scan_dir.setText(self.stored_settings.pre_scan_dir)

                pre_scan_epsg = self.my_dialog.qle_pre_scan_epsg.text()
                if pre_scan_epsg:
                    self.stored_settings.pre_scan_epsg = pre_scan_epsg
                else:
                    self.stored_settings.pre_scan_epsg = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
                    self.my_dialog.qle_pre_scan_epsg.setText(self.stored_settings.pre_scan_epsg)

                pre_scan_patterns = self.my_dialog.qle_pre_scan_patterns.text()

                if pre_scan_patterns:
                    self.stored_settings.pre_scan_patterns = pre_scan_patterns
                else:
                    # trigger the signal
                    self.my_dialog.qcb_select_pre_scan_patterns.setCurrentIndex(1)

                self.stored_settings.pre_scan_sub_dirs = self.my_dialog.qcb_pre_scan_sub_dirs.isChecked()

                # re-scan the widget
                pre_scan_fields, pre_scan_rel_root_dir = self.file_meta_extractor.parse_pre_scan_widget()
                self.stored_settings.pre_scan_fields = pre_scan_fields
                self.stored_settings.pre_scan_rel_root_dir = pre_scan_rel_root_dir

            if 'SYNC_SETTINGS' in use_cases:
                self.stored_settings.sync_source_layer_id = ''
                selected_sync_lyr = self.my_dialog.qcbn_sync_source_layer.currentData(Qt_Roles.RETURN_VALUE)
                if selected_sync_lyr:
                    self.stored_settings.sync_source_layer_id = selected_sync_lyr.id()

                self.stored_settings.sync_target_layer_id = ''
                selected_sync_lyr = self.my_dialog.qcbn_sync_target_layer.currentData(Qt_Roles.RETURN_VALUE)
                if selected_sync_lyr:
                    self.stored_settings.sync_target_layer_id = selected_sync_lyr.id()

                self.stored_settings.sync_source_abs_path_field = self.my_dialog.qcb_sync_source_abs_path_field.currentText()
                self.stored_settings.sync_source_rel_path_field = self.my_dialog.qcb_sync_source_rel_path_field.currentText()
                self.stored_settings.sync_target_abs_path_field = self.my_dialog.qcb_sync_target_abs_path_field.currentText()

                self.stored_settings.sync_fields = {}

                for rc in range(self.my_dialog.qtw_sync_mappings.model().rowCount()):
                    sync_source_qlwi = self.my_dialog.qtw_sync_mappings.item(rc, 0)
                    sync_source_field_name = sync_source_qlwi.data(QtCore.Qt.DisplayRole)
                    sync_target_qlwi = self.my_dialog.qtw_sync_mappings.item(rc, 2)
                    sync_target_field_name = sync_target_qlwi.data(QtCore.Qt.DisplayRole)
                    self.stored_settings.sync_fields[sync_target_field_name] = sync_source_field_name

                self.stored_settings.sync_file_mode = ''
                if self.my_dialog.qrb_sync_file_mode_copy.isChecked():
                    self.stored_settings.sync_file_mode = 'copy'
                elif self.my_dialog.qrb_sync_file_mode_keep.isChecked():
                    self.stored_settings.sync_file_mode = 'keep'

                self.stored_settings.sync_existing_file_mode = ''
                if self.my_dialog.qcb_sync_existing_file_mode.currentData():
                    self.stored_settings.sync_existing_file_mode = self.my_dialog.qcb_sync_existing_file_mode.currentData()

                self.stored_settings.sync_existing_feature_mode = ''
                if self.my_dialog.qcb_sync_existing_feature_mode.currentData():
                    self.stored_settings.sync_existing_feature_mode = self.my_dialog.qcb_sync_existing_feature_mode.currentData()

                self.stored_settings.sync_update_geometries = self.my_dialog.qcb_sync_update_geometries.isChecked()

                self.stored_settings.sync_target_dir = self.my_dialog.qle_sync_target_dir.text()

            if 'POST_SCAN_SETTINGS' in use_cases:
                self.stored_settings.post_scan_layer_id = ''
                self.stored_settings.post_scan_abs_path_field = ''
                self.stored_settings.post_scan_fields = {}
                self.stored_settings.post_scan_rel_root_dir = ''
                self.stored_settings.post_scan_preserve_existing = self.my_dialog.qcb_post_scan_preserve_existing.isChecked()
                self.stored_settings.post_scan_update_geometry_from_exif = self.my_dialog.qcb_post_scan_update_geometry_from_exif.isChecked()
                post_scan_layer = self.my_dialog.qcbn_post_scan_layer.currentData(Qt_Roles.RETURN_VALUE)
                if post_scan_layer:
                    self.stored_settings.post_scan_layer_id = post_scan_layer.id()

                    self.stored_settings.post_scan_abs_path_field = self.my_dialog.qcb_post_scan_abs_path_field.currentText()

                    post_scan_fields, post_scan_rel_root_dir = self.file_meta_extractor.parse_post_scan_widget()
                    self.stored_settings.post_scan_fields = post_scan_fields
                    self.stored_settings.post_scan_rel_root_dir = post_scan_rel_root_dir

    def s_start_pre_scan(self):
        """start PreScan-Process"""
        t_1 = time.perf_counter_ns()
        tab = '&nbsp;' * 3
        process_log = []

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} start PreScan")

        self.my_dialog.qprb_pre_scan.setValue(0)
        self.my_dialog.qlbl_pre_scan_progress.clear()

        self.dlg_parse_settings(['PRE_SCAN_SETTINGS'])

        check_ok, check_log = self.sys_check_settings(['PRE_SCAN_SETTINGS'])

        process_log += check_log

        if check_ok:
            process_log.append(f"{tab}✓ pre_scan_dir '{self.stored_settings.pre_scan_dir}'")
            process_log.append(f"{tab}✓ pre_scan_sub_dirs '{self.stored_settings.pre_scan_sub_dirs}'")
            process_log.append(f"{tab}✓ pre_scan_patterns '{self.stored_settings.pre_scan_patterns}'")
            process_log.append(f"{tab}✓ pre_scan_epsg '{self.stored_settings.pre_scan_epsg}'")
            pre_scan_crs = qgis._core.QgsCoordinateReferenceSystem(self.stored_settings.pre_scan_epsg)

            # get list of files:
            scan_result = MyTools.scan_files(self.stored_settings.pre_scan_dir, self.stored_settings.pre_scan_patterns, self.stored_settings.pre_scan_sub_dirs)

            if scan_result:
                num_files = len(scan_result)
                process_log.append(f"{tab}✓ num_files {num_files}")

                # very many files => security check to avoid unintentionally long running processes
                if num_files > 1000:
                    dialog_result = QtWidgets.QMessageBox.question(
                        None,
                        f"FileSync",
                        f"The PreScan resulted in {num_files} files!\n\nContinue?",
                        buttons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        defaultButton=QtWidgets.QMessageBox.No
                    )

                    if not dialog_result or dialog_result == QtWidgets.QMessageBox.No:
                        return

                self.my_dialog.sub_wdg_pre_scan_progress.setVisible(True)
                self.my_dialog.qprb_pre_scan.setMinimum(0)
                self.my_dialog.qprb_pre_scan.setMaximum(num_files)
                self.my_dialog.qprb_pre_scan.setValue(0)
                self.my_dialog.qlbl_pre_scan_progress.setText('')

                layer_names = [layer.name() for layer in qgis._core.QgsProject.instance().mapLayers().values()]
                template = f"pre_scan_result {self.stored_settings.pre_scan_dir}_{{curr_i}}"
                pre_scan_layer_name = MyTools.get_unique_string(layer_names, template, 1)

                # create the new temorary layer
                # geometry-type PointZ to store GPS-altitude if exists
                pre_scan_vl = qgis._core.QgsVectorLayer(f"PointZ?crs={self.stored_settings.pre_scan_epsg}&index=yes", pre_scan_layer_name, "memory")

                # populate fields
                field_list = {}
                for meta_name, field_name in self.stored_settings.pre_scan_fields.items():
                    extract_field = self.file_meta_extractor.get_extract_field(meta_name, field_name)
                    if extract_field:
                        field_list[meta_name] = extract_field

                pre_scan_vl.dataProvider().addAttributes(field_list.values())
                pre_scan_vl.updateFields()
                qgis._core.QgsProject.instance().addMapLayer(pre_scan_vl)

                process_log.append(f"{tab}✓ temporary point-layer created: '{pre_scan_vl.name()}'")

                # add layer-actions
                FeatureDigitizeMapTool.add_show_form_action(pre_scan_vl)
                FeatureDigitizeMapTool.add_show_file_action(pre_scan_vl, self.stored_settings.pre_scan_fields.get('abs_path'))
                FeatureDigitizeMapTool.add_show_feature_action(pre_scan_vl, self.stored_settings.pre_scan_fields.get('gps_img_direction'))

                # Exif-GPS-Koordinaten => WGS 84 => EPSG 4326
                wgs_84_crs = qgis._core.QgsCoordinateReferenceSystem("EPSG:4326")
                tr_wgs_2_vl = qgis._core.QgsCoordinateTransform(wgs_84_crs, pre_scan_crs, qgis._core.QgsProject.instance())

                pre_scan_vl.startEditing()

                process_log.append(f"{tab}File-Iteration-Start...")
                fc = 0
                for posix_path in scan_result:
                    # runtime-environment-independent: allways slash as directory separator
                    fc += 1
                    self.my_dialog.qprb_pre_scan.setValue(fc)
                    self.my_dialog.qlbl_pre_scan_progress.setText(f"File {fc} from {num_files}")
                    feature = qgis._core.QgsFeature(pre_scan_vl.dataProvider().fields())

                    extract_ok, feature_altered, extract_log = self.file_meta_extractor.extract_file_metas(posix_path, feature, self.stored_settings.pre_scan_fields, self.stored_settings.pre_scan_rel_root_dir, False, True, tr_wgs_2_vl)

                    process_log += extract_log

                    pre_scan_vl.dataProvider().addFeature(feature)
                    process_log.append(f"{tab}{tab}✔ {posix_path.as_posix()}")

                process_log.append(f"{tab}...File-Iteration-End")
                pre_scan_vl.commitChanges()

                self.iface.showAttributeTable(pre_scan_vl)

            else:
                process_log.append(f"<b>{tab}⭍ no files for '{self.stored_settings.pre_scan_dir}' with pattern '{self.stored_settings.pre_scan_patterns}'</b>")
        else:
            process_log.append(f"<b>{tab}⭍ Settings invalid...</b>")

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} end PreScan, runtime {(time.perf_counter_ns() - t_1) * 1e-9:.5f} s")

        self.tool_append_to_log_history(process_log)

    def scc_select_pre_scan_crs(self, *arg, **kwargs):
        """sets self.stored_settings.pre_scan_epsg via QgsProjectionSelectionDialog (Projection for temporary PreScan-Layer)"""
        # Rev. 2025-06-11
        select_crs_dialog = qgis.gui.QgsProjectionSelectionDialog()
        select_crs_dialog.exec_()
        self.stored_settings.pre_scan_epsg = select_crs_dialog.crs().authid()
        self.my_dialog.qle_pre_scan_epsg.setText(self.stored_settings.pre_scan_epsg)

    def scc_select_pre_scan_dir(self, *arg, **kwargs):
        """set self.stored_settings.pre_scan_dir via QFileDialog"""
        if self.stored_settings.pre_scan_dir and os.path.isdir(self.stored_settings.pre_scan_dir):
            dlg_start_dir = self.stored_settings.pre_scan_dir
        else:
            dlg_start_dir = os.path.expanduser('~')

        pre_scan_dir = QtWidgets.QFileDialog.getExistingDirectory(self.my_dialog, 'select pre_scan_dir', dlg_start_dir, QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)
        self.stored_settings.pre_scan_dir = pre_scan_dir
        self.my_dialog.qle_pre_scan_dir.setText(self.stored_settings.pre_scan_dir)

    def scc_select_sync_target_dir(self, *arg, **kwargs):
        """set self.stored_settings.sync_target_dir  via QFileDialog"""
        if self.stored_settings.sync_target_dir and os.path.isdir(self.stored_settings.sync_target_dir):
            dlg_start_dir = self.stored_settings.sync_target_dir
        else:
            dlg_start_dir = os.path.expanduser('~')

        sync_target_dir = QtWidgets.QFileDialog.getExistingDirectory(self.my_dialog, 'select sync_target_dir', dlg_start_dir, QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)
        self.stored_settings.sync_target_dir = sync_target_dir
        self.my_dialog.qle_sync_target_dir.setText(self.stored_settings.sync_target_dir)

    def unload(self):
        """standard-to_implement-function for each plugin:
        reset the GUI,
        triggered by plugin-deactivation, project-close, QGis-Quit
        """
        # Rev. 2025-06-11
        self.sys_store_settings()

        self.iface.removeToolBarIcon(self.qact_open_dialog)
        self.iface.removeToolBarIcon(self.qact_show_help)
        self.iface.removePluginMenu('FileSync', self.qact_open_dialog)
        self.iface.removePluginMenu('FileSync', self.qact_show_help)

        if self.my_dialog:
            self.my_dialog.close()
            del self.my_dialog

        # remove toolbar
        # calling deleteLater() on the toolbar object schedules it for deletion and completely removes it also from the view -> toolbars menu
        if self.file_sync_toolbar:
            self.file_sync_toolbar.deleteLater()
            del self.file_sync_toolbar

        try:
            # cut project-signal/slot-connections
            for conn_id in self.project_connections:
                qgis._core.QgsProject.instance().disconnect(conn_id)
            self.project_connections = []
        except RuntimeError as e:
            # RuntimeError: wrapped C/C++ object of type QgsVectorLayer has been deleted
            pass

        # self.gui_unload_layer_actions()

    def gui_unload_layer_actions(self):
        """removes all actions from all layers (orphaned) on unload"""
        # Rev. 2025-06-11
        for cl in qgis.core.QgsProject.instance().mapLayers().values():
            if cl.type() == qgis.core.QgsMapLayerType.VectorLayer:
                # Note: action_id is not unique!
                action_list = [action for action in cl.actions().actions() if action.id() in [FeatureDigitizeMapTool.georef_act_id, FeatureDigitizeMapTool.show_file_act_id]]
                for action in action_list:
                    cl.actions().removeAction(action.id())

                if action_list:
                    cl.reload()

    def sys_restore_settings(self):
        """restore last-usage-settings from ini-file (Name => self.ini_storage_file_name file)
        Unix: /home/_user_name_/.QGis_FileSync_Plugin.ini
        Windows: c:/Users/_user_name_/.QGis_FileSync_Plugin.ini

        Note:
            Settings are stored independend from QgsProject, so all layer- and field-references probably do not match if a new or an other project ist openend
        """
        # Rev. 2025-06-11

        tab = '&nbsp;' * 3

        self.restore_settings_log += [f"{time.strftime('%H:%M:%S', time.localtime())} sys_restore_settings"]

        self.stored_settings = StoredSettings()

        # for prop_name in StoredSettings._str_props:
        #     restored_value, type_conversion_ok = qgis._core.QgsProject.instance().readEntry('FileSync', prop_name)
        #     if type_conversion_ok:
        #         debug_log(prop_name,restored_value)
        #         setattr(self.stored_settings, prop_name, restored_value)
        #
        #
        #
        # check_ok, check_log = self.sys_check_settings()
        # # note: restore_settings_log ist shown on first dlg_init
        # self.restore_settings_log += check_log
        #
        # return

        int_types = [
            QtCore.QVariant.Int,
            QtCore.QVariant.LongLong,
            QtCore.QVariant.UInt,
            QtCore.QVariant.ULongLong,
        ]

        config_object = ConfigParser()

        config_object.optionxform = str

        ini_path = Path(f'~/{self.ini_storage_file_name}')

        parsed_file_names = config_object.read(ini_path.expanduser())

        if parsed_file_names:
            self.restore_settings_log += [f"{tab}restored settings from file '{ini_path.expanduser()}'"]
            if config_object.has_section('PRE_SCAN_SETTINGS'):
                stored_settings_dict = config_object["PRE_SCAN_SETTINGS"]
                # parse "as is", no check here
                self.stored_settings.pre_scan_dir = stored_settings_dict.get('pre_scan_dir', '')
                self.stored_settings.pre_scan_epsg = stored_settings_dict.get('pre_scan_epsg', '')

                # Note: == 'True' because the ini-contents are read as strings
                self.stored_settings.pre_scan_sub_dirs = stored_settings_dict.get('pre_scan_sub_dirs', '') == 'True'
                self.stored_settings.pre_scan_patterns = stored_settings_dict.get('pre_scan_patterns', '')

                self.stored_settings.pre_scan_rel_root_dir = stored_settings_dict.get('pre_scan_rel_root_dir', '')

            if config_object.has_section('PRE_SCAN_FIELDS'):
                self.stored_settings.pre_scan_fields = dict(config_object["PRE_SCAN_FIELDS"])

            if config_object.has_section('SYNC_SETTINGS'):
                stored_settings_dict = config_object["SYNC_SETTINGS"]

                # no check here
                self.stored_settings.sync_source_layer_id = stored_settings_dict.get('sync_source_layer_id', '')
                self.stored_settings.sync_target_layer_id = stored_settings_dict.get('sync_target_layer_id', '')
                self.stored_settings.sync_source_abs_path_field = stored_settings_dict.get('sync_source_abs_path_field', '')
                self.stored_settings.sync_source_rel_path_field = stored_settings_dict.get('sync_source_rel_path_field', '')
                self.stored_settings.sync_target_abs_path_field = stored_settings_dict.get('sync_target_abs_path_field', '')
                self.stored_settings.sync_file_mode = stored_settings_dict.get('sync_file_mode', '')
                self.stored_settings.sync_existing_file_mode = stored_settings_dict.get('sync_existing_file_mode', '')
                self.stored_settings.sync_existing_feature_mode = stored_settings_dict.get('sync_existing_feature_mode', '')
                self.stored_settings.sync_update_geometries = stored_settings_dict.get('sync_update_geometries', '') == 'True'

                if stored_settings_dict.get('sync_target_dir'):
                    if os.path.isdir(stored_settings_dict.get('sync_target_dir', '')):
                        self.stored_settings.sync_target_dir = stored_settings_dict.get('sync_target_dir', '')

            if config_object.has_section('SYNC_FIELDS'):
                store_sync_fields = dict(config_object["SYNC_FIELDS"])
                for title, mapping in store_sync_fields.items():
                    # title => field_0, field_1... => only to get valid and unique ConfigParser-ini-key, content not used
                    # mapping => f"{sync_target_field_name}{self.ini_delimiter}{sync_source_field_name}"
                    try:
                        (sync_target_field_name, sync_source_field_name) = mapping.split(self.ini_delimiter)
                        sync_target_field = self.tool_get_sync_target_field(sync_target_field_name)
                        sync_source_field = self.tool_get_sync_source_field(sync_source_field_name)
                        if sync_target_field and sync_source_field and (sync_target_field.type() == sync_source_field.type() or (sync_source_field.type() in int_types and sync_target_field.type() in int_types)):
                            self.stored_settings.sync_fields[sync_target_field_name] = sync_source_field_name
                    except Exception as e:
                        pass

            if config_object.has_section('POST_SCAN_SETTINGS'):
                stored_settings_dict = config_object["POST_SCAN_SETTINGS"]

                # no check here
                self.stored_settings.post_scan_layer_id = stored_settings_dict.get('post_scan_layer_id', '')
                self.stored_settings.post_scan_abs_path_field = stored_settings_dict.get('post_scan_abs_path_field', '')
                self.stored_settings.post_scan_rel_root_dir = stored_settings_dict.get('post_scan_rel_root_dir', '')
                self.stored_settings.post_scan_preserve_existing = stored_settings_dict.get('post_scan_preserve_existing', '') == 'True'
                self.stored_settings.post_scan_update_geometry_from_exif = stored_settings_dict.get('post_scan_update_geometry_from_exif', '') == 'True'

            if config_object.has_section('POST_SCAN_FIELDS'):
                self.stored_settings.post_scan_fields = dict(config_object["POST_SCAN_FIELDS"])

            check_ok, check_log = self.sys_check_settings()
            # note: restore_settings_log ist shown on first dlg_init
            self.restore_settings_log += check_log

        else:
            self.restore_settings_log += [f"{tab}no stored settings"]

    def sys_store_settings(self):
        """store current settings to ini-file (Name => self.ini_storage_file_name file)
        Unix: /home/_user_name_/.QGis_FileSync_Plugin.ini
        Windows: c:/Users/_user_name_/.QGis_FileSync_Plugin.ini

        Note:
            Settings are stored independend from QgsProject, so all layer- and field-references probably do not match if a new or an other project ist openend
        """
        # Rev. 2025-06-11

        # Create a ConfigParser object
        # https://docs.python.org/3/library/configparser.html
        config_object = ConfigParser()
        # Keys in der ini-Datei case-sensitive (default: all lowercase)
        config_object.optionxform = str
        # stringify self.stored_settings
        #  all stored properties must be string, else TypeError("option values must be strings")
        # caveat: no None, NULL, True/False as boolean, but stringified as '0', '1', 'True', 'False' and restore these strings in sys_restore_settings

        self.dlg_parse_settings()

        check_ok, check_log = self.sys_check_settings()

        config_object["PRE_SCAN_SETTINGS"] = {
            'pre_scan_dir': self.stored_settings.pre_scan_dir,
            'pre_scan_epsg': self.stored_settings.pre_scan_epsg,
            'pre_scan_patterns': self.stored_settings.pre_scan_patterns,
            'pre_scan_sub_dirs': str(self.stored_settings.pre_scan_sub_dirs),
            'pre_scan_rel_root_dir': self.stored_settings.pre_scan_rel_root_dir,
        }

        config_object["PRE_SCAN_FIELDS"] = self.stored_settings.pre_scan_fields

        config_object["SYNC_SETTINGS"] = {
            'sync_source_layer_id': self.stored_settings.sync_source_layer_id,
            'sync_target_layer_id': self.stored_settings.sync_target_layer_id,
            'sync_source_abs_path_field': self.stored_settings.sync_source_abs_path_field,
            'sync_source_rel_path_field': self.stored_settings.sync_source_rel_path_field,
            'sync_target_abs_path_field': self.stored_settings.sync_target_abs_path_field,
            'sync_target_dir': self.stored_settings.sync_target_dir,
            'sync_file_mode': self.stored_settings.sync_file_mode,
            'sync_existing_file_mode': self.stored_settings.sync_existing_file_mode,
            'sync_existing_feature_mode': self.stored_settings.sync_existing_feature_mode,
            'sync_update_geometries': str(self.stored_settings.sync_update_geometries),

        }

        store_sync_fields = {}
        # one disadvantage of ConfigParser: special characters in keys, especially if they are the ConfigParser-delimiters, default '='
        # Delimiters are substrings that delimit keys from values within a section.
        # The first occurrence of a delimiting substring on a line is considered a delimiter.
        # This means values (but not keys) can contain the delimiters.
        # therfore a special syntax for storing self.stored_settings.sync_fields
        for idx, (sync_target_field_name, sync_source_field_name) in enumerate(self.stored_settings.sync_fields.items()):
            store_sync_fields[f'field_{idx}'] = f"{sync_target_field_name}{self.ini_delimiter}{sync_source_field_name}"

        config_object["SYNC_FIELDS"] = store_sync_fields

        config_object["POST_SCAN_SETTINGS"] = {
            'post_scan_layer_id': self.stored_settings.post_scan_layer_id,
            'post_scan_abs_path_field': self.stored_settings.post_scan_abs_path_field,
            'post_scan_rel_root_dir': self.stored_settings.post_scan_rel_root_dir,
            'post_scan_preserve_existing': str(self.stored_settings.post_scan_preserve_existing),
            'post_scan_update_geometry_from_exif': str(self.stored_settings.post_scan_update_geometry_from_exif)
        }

        config_object["POST_SCAN_FIELDS"] = self.stored_settings.post_scan_fields

        # Write the configuration to a file named self.ini_storage_file_name inside current user directory
        ini_path = Path(f'~/{self.ini_storage_file_name}')
        with open(ini_path.expanduser(), 'w') as conf:
            config_object.write(conf)

    def sys_check_settings(self, use_cases=None) -> tuple:
        """check stored settings
        Layer exists? Field exists? Field-Types match? Directory exists? Projection valid?...
        :param use_cases: if None, all three use_cases are checked
        :returns: tuple(check_ok,process_log)"""
        # Rev. 2025-06-11

        if not use_cases:
            use_cases = ['PRE_SCAN_SETTINGS', 'SYNC_SETTINGS', 'POST_SCAN_SETTINGS']
        tab = '&nbsp;' * 3
        check_ok = True
        process_log = []

        process_log.append(f"{time.strftime('%H:%M:%S', time.localtime())} CheckSettings")

        if 'PRE_SCAN_SETTINGS' in use_cases:

            process_log.append(f"{tab}PRE_SCAN_SETTINGS")

            process_log.append(f"{tab}{tab}pre_scan_dir '{self.stored_settings.pre_scan_dir}'")
            if self.stored_settings.pre_scan_dir:
                if not Path(self.stored_settings.pre_scan_dir).is_dir():
                    process_log.append(f"<b>{tab}{tab}⭍ directory not found or no directory</b>")
                    check_ok = False
                    self.stored_settings.pre_scan_dir = ''
            else:
                check_ok = False

            if not self.stored_settings.pre_scan_epsg:
                self.stored_settings.pre_scan_epsg = self.iface.mapCanvas().mapSettings().destinationCrs().authid()

            pre_scan_crs = qgis._core.QgsCoordinateReferenceSystem(self.stored_settings.pre_scan_epsg)
            if not pre_scan_crs.isValid():
                self.stored_settings.pre_scan_epsg = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
            process_log.append(f"{tab}{tab}pre_scan_epsg '{self.stored_settings.pre_scan_epsg}'")

            if not self.stored_settings.pre_scan_patterns:
                self.stored_settings.pre_scan_patterns = '*.*'

            process_log.append(f"{tab}{tab}pre_scan_patterns '{self.stored_settings.pre_scan_patterns}'")

            process_log.append(f"{tab}{tab}pre_scan_sub_dirs '{self.stored_settings.pre_scan_sub_dirs}'")

            if 'rel_path' in self.stored_settings.pre_scan_fields:
                process_log.append(f"{tab}{tab}pre_scan_rel_root_dir '{self.stored_settings.pre_scan_rel_root_dir}'")
                if self.stored_settings.pre_scan_rel_root_dir:
                    if not Path(self.stored_settings.pre_scan_rel_root_dir).is_dir():
                        process_log.append(f"<b>{tab}{tab}⭍ directory not found or no directory</b>")
                        self.stored_settings.pre_scan_rel_root_dir = ''
                        check_ok = False
                else:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ meta 'rel_path' without valid pre_scan_rel_root_dir</b>")
                    check_ok = False

            process_log.append(f"{tab}{tab}pre_scan_fields:")
            for meta_name, field_name in self.stored_settings.pre_scan_fields.items():
                process_log.append(f"{tab}{tab}{tab}{meta_name} -> {field_name}")

        if 'SYNC_SETTINGS' in use_cases:
            process_log.append(f"{tab}SYNC_SETTINGS")

            process_log.append(f"{tab}{tab}sync_source_layer_id '{self.stored_settings.sync_source_layer_id}'")
            if not self.tool_get_sync_source_layer():
                if self.stored_settings.sync_source_layer_id:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_source_layer not found</b>")
                self.stored_settings.sync_source_layer_id = ''
                self.stored_settings.sync_source_abs_path_field = ''
                self.stored_settings.sync_source_rel_path_field = ''
                self.stored_settings.sync_fields = {}
                check_ok = False

            process_log.append(f"{tab}{tab}sync_target_layer_id '{self.stored_settings.sync_target_layer_id}'")
            if not self.stored_settings.sync_target_layer_id or not self.tool_get_sync_target_layer():
                if self.stored_settings.sync_target_layer_id:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_target_layer not found</b>")
                self.stored_settings.sync_target_layer_id = ''
                self.stored_settings.sync_target_abs_path_field = ''
                self.stored_settings.sync_fields = {}
                check_ok = False

            sync_source_layer = self.tool_get_sync_source_layer()
            sync_target_layer = self.tool_get_sync_target_layer()

            process_log.append(f"{tab}{tab}sync_source_abs_path_field '{self.stored_settings.sync_source_abs_path_field}'")
            if not self.tool_get_sync_source_field(self.stored_settings.sync_source_abs_path_field):
                if self.stored_settings.sync_source_abs_path_field:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_source_abs_path_field not found</b>")
                self.stored_settings.sync_source_abs_path_field = ''
                check_ok = False

            process_log.append(f"{tab}{tab}sync_source_rel_path_field '{self.stored_settings.sync_source_rel_path_field}'")
            if self.stored_settings.sync_source_rel_path_field and not self.tool_get_sync_source_field(self.stored_settings.sync_source_rel_path_field):
                process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_source_rel_path_field not found</b>")
                self.stored_settings.sync_source_rel_path_field = ''

            process_log.append(f"{tab}{tab}sync_target_abs_path_field '{self.stored_settings.sync_target_abs_path_field}'")
            if not self.tool_get_sync_target_field(self.stored_settings.sync_target_abs_path_field):
                if self.stored_settings.sync_target_abs_path_field:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_target_abs_path_field not found</b>")
                self.stored_settings.sync_target_abs_path_field = ''
                check_ok = False

            if not self.stored_settings.sync_file_mode in ['keep', 'copy']:
                self.stored_settings.sync_file_mode = 'keep'

            process_log.append(f"{tab}{tab}sync_file_mode '{self.stored_settings.sync_file_mode}'")

            if self.stored_settings.sync_file_mode == 'copy':
                if not self.stored_settings.sync_existing_file_mode in ['replace', 'rename', 'skip']:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_existing_file_mode missing</b>")
                else:
                    process_log.append(f"{tab}{tab}sync_existing_file_mode '{self.stored_settings.sync_existing_file_mode}'")

                process_log.append(f"{tab}{tab}sync_target_dir '{self.stored_settings.sync_target_dir}'")
                if self.stored_settings.sync_target_dir:
                    if not Path(self.stored_settings.sync_target_dir).is_dir():
                        process_log.append(f"<b>{tab}{tab}⭍ directory not found or no directory, reset sync_target_dir</b>")
                        self.stored_settings.sync_target_dir = ''
                        check_ok = False
                else:
                    process_log.append(f"<b>{tab}{tab}⭍ sync_file_mode 'copy' without sync_target_dir...</b>")
                    check_ok = False

            process_log.append(f"{tab}{tab}sync_update_geometries '{self.stored_settings.sync_update_geometries}'")
            if sync_source_layer and sync_target_layer and self.stored_settings.sync_update_geometries:
                point_wkb_types = [
                    qgis._core.QgsWkbTypes.Point,
                    qgis._core.QgsWkbTypes.PointZ,
                    qgis._core.QgsWkbTypes.PointM,
                    qgis._core.QgsWkbTypes.PointZM,
                ]
                if sync_source_layer.dataProvider().wkbType() in point_wkb_types:
                    if sync_target_layer.dataProvider().wkbType() in point_wkb_types:
                        tr_source_2_target = qgis._core.QgsCoordinateTransform(sync_source_layer.crs(), sync_target_layer.crs(), qgis._core.QgsProject.instance())
                        if not tr_source_2_target.isValid():
                            process_log.append(f"<b>{tab}⭍ Coordinate-Transformation '{sync_source_layer.crs().authid()} -> {sync_target_layer.crs().authid()}' not valid</b>")
                            check_ok = False
                    else:
                        process_log.append(f"<b>{tab}⭍ 'update geometries' checked, but target-layer-geometry-type != 'Point'</b>")
                        check_ok = False
                else:
                    process_log.append(f"<b>{tab}⭍ 'update geometries' checked, but source-layer-geometry-type != 'Point'</b>")
                    check_ok = False

            if not self.stored_settings.sync_existing_feature_mode in ['update_overwrite', 'update_preserve', 'insert', 'replace', 'skip']:
                process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_existing_feature_mode missing</b>")
            else:
                process_log.append(f"{tab}{tab}sync_existing_feature_mode '{self.stored_settings.sync_existing_feature_mode}'")

            process_log.append(f"{tab}{tab}sync_fields:")
            if self.stored_settings.sync_fields:
                int_types = [
                    QtCore.QVariant.Int,
                    QtCore.QVariant.LongLong,
                    QtCore.QVariant.UInt,
                    QtCore.QVariant.ULongLong,
                ]
                # check existence and mapping-validity
                for sync_target_field_name, sync_source_field_name in self.stored_settings.sync_fields.items():
                    sync_source_field = self.tool_get_sync_source_field(sync_source_field_name)
                    sync_target_field = self.tool_get_sync_target_field(sync_target_field_name)
                    if sync_target_field:
                        if sync_source_field:
                            if sync_source_field.type() == sync_target_field.type() or (sync_source_field.type() in int_types and sync_target_field.type() in int_types):
                                process_log.append(f"{tab}{tab}{tab}{sync_source_field_name} -> {sync_target_field_name}")
                            else:
                                process_log.append(f"<b>{tab}{tab}{tab}⭍ Fields '{sync_source_field_name}' -> '{sync_target_field_name}' with unsuitable types</b>")
                                del self.stored_settings.sync_fields[sync_target_field_name]
                                check_ok = False
                        else:
                            process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_source_field {sync_source_field_name} not found</b>")
                            del self.stored_settings.sync_fields[sync_target_field_name]
                            check_ok = False
                    else:
                        process_log.append(f"<b>{tab}{tab}{tab}⭍ sync_target_field {sync_target_field_name} not found</b>")
                        del self.stored_settings.sync_fields[sync_target_field_name]
                        check_ok = False
            else:
                process_log.append(f"{tab}{tab}{tab}no sync_fields defined")

        if 'POST_SCAN_SETTINGS' in use_cases:
            process_log.append(f"{tab}POST_SCAN_SETTINGS")

            process_log.append(f"{tab}{tab}post_scan_layer_id '{self.stored_settings.post_scan_layer_id}'")
            if not self.stored_settings.post_scan_layer_id or not self.tool_get_post_scan_layer():
                if self.stored_settings.post_scan_layer_id:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ post_scan_layer not found</b>")
                    check_ok = False

            process_log.append(f"{tab}{tab}post_scan_preserve_existing '{self.stored_settings.post_scan_preserve_existing}'")
            process_log.append(f"{tab}{tab}post_scan_update_geometry_from_exif '{self.stored_settings.post_scan_update_geometry_from_exif}'")

            if self.stored_settings.post_scan_abs_path_field:
                process_log.append(f"{tab}{tab}post_scan_abs_path_field '{self.stored_settings.post_scan_abs_path_field}'")
                post_scan_abs_path_field = self.tool_get_post_scan_field(self.stored_settings.post_scan_abs_path_field)
                if not post_scan_abs_path_field:
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ post_scan_abs_path_field not found</b>")
            else:
                process_log.append(f"<b>{tab}{tab}{tab}⭍ post_scan_abs_path_field not defined</b>")
                check_ok = False

            if self.stored_settings.post_scan_layer_id:

                if self.stored_settings.post_scan_update_geometry_from_exif:
                    point_wkb_types = [
                        qgis._core.QgsWkbTypes.Point,
                        qgis._core.QgsWkbTypes.PointZ,
                        qgis._core.QgsWkbTypes.PointM,
                        qgis._core.QgsWkbTypes.PointZM,
                    ]
                    post_scan_layer = self.tool_get_post_scan_layer()
                    if not (post_scan_layer and post_scan_layer.isValid() and post_scan_layer.type() == qgis._core.Qgis.LayerType.VectorLayer and post_scan_layer.dataProvider().wkbType() in point_wkb_types):
                        process_log.append(f"<b>{tab}{tab}{tab}⭍ 'update geometries' selected, but layer-geometry-type != point</b>")
                        check_ok = False

                if self.stored_settings.post_scan_abs_path_field and not self.tool_get_post_scan_field(self.stored_settings.post_scan_abs_path_field):
                    process_log.append(f"<b>{tab}{tab}{tab}⭍ post_scan_abs_path_field not found</b>")
                    check_ok = False

                process_log.append(f"{tab}{tab}post_scan_fields:")
                for meta_name, field_name in self.stored_settings.post_scan_fields.items():
                    process_log.append(f"{tab}{tab}{tab}{meta_name} -> {field_name}")
                    if self.stored_settings.post_scan_layer_id and not self.tool_get_post_scan_field(field_name):
                        process_log.append(f"<b>{tab}{tab}{tab}⭍ field '{field_name}' not found</b>")
                        check_ok = False

                if 'rel_path' in self.stored_settings.post_scan_fields:
                    process_log.append(f"{tab}{tab}post_scan_rel_root_dir '{self.stored_settings.post_scan_rel_root_dir}'")
                    if self.stored_settings.post_scan_rel_root_dir:
                        if not Path(self.stored_settings.post_scan_rel_root_dir).is_dir():
                            process_log.append(f"<b>{tab}{tab}⭍ post_scan_rel_root_dir not valid</b>")
                            check_ok = False
                    else:
                        process_log.append(f"<b>{tab}{tab}⭍ post_scan_rel_root_dir missing</b>")
                        check_ok = False

        return check_ok, process_log
