#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin FileSync:
* some Tool-Functions

********************************************************************

* Date                 : 2025-04-11
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

.. note::
    * to import these methods for usage in python console:
    * from FileSync import tools
    * import FileSync.tools.MyTools
    * from FileSync.tools.MyTools import re_open_attribute_tables

********************************************************************
"""
import os, sys, re, tempfile
import hashlib
from pathlib import Path
import typing
from typing import Any
from datetime import datetime

import qgis
from PyQt5 import QtCore, QtWidgets



def qcbx_select_by_value(qcbx:QtWidgets.QComboBox, value:Any, role:QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole):
    """Tool-functtion to select an item in a QComboBox by its valueW
    :param qcbx: QComboBox
    :param value:
    :param role: default QtCore.Qt.DisplayRole => Display-Value in QComboBox, often used QtCore.Qt.UserRole, the value used as second parameter for QComboBox.addItem(display_value, user_value)
    """
    matching_items = qcbx.model().match(qcbx.model().index(0, 0), role, value, 1, QtCore.Qt.MatchExactly)
    if matching_items:
        with QtCore.QSignalBlocker(qcbx):
            qcbx.setCurrentIndex(matching_items[0].row())

def get_unique_string(used_strings: list, template: str, start_i: int = 1) -> str:
    """get unique string replacing Wildcard {curr_i} with incremented integer
    :param used_strings: List of already used strings, f.e. table-names in a GeoPackage or layer in QGis-Project [layer.name() for layer in  qgis._core.QgsProject.instance().mapLayers().values()]
    :param template: template with Wildcard {curr_i}
    :param start_i: start index for incrementing, usually 1
    """
    # avoids endless "while True" below, if '{curr_i}' is missing in template
    if not '{curr_i}' in template:
        template += '{curr_i}'

    while True:
        return_string = template.format(curr_i=start_i)
        if not return_string in used_strings:
            return return_string
        start_i += 1


def get_file_hash(file_path: str | Path, hash_alg: str = 'sha1') -> str:
    """
    get a hash-value for a file, used to identify duplicates
    :param file_path:
    :param hash_alg: md5,sha1,sha256... see https://docs.python.org/3/library/hashlib.html
    :return: str, the hash-value, unique for a file, f.e. for storage in database
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if file_path.exists():
        with open(file_path, "rb") as f:
            file_hash = hashlib.new(hash_alg)

            while chunk := f.read(8192):
                file_hash.update(chunk)

        # digest => binary
        # hexdigest => printable/storable str:
        return file_hash.hexdigest()
    else:
        raise FileNotFoundError(f"File '{file_path}' not found")

def create_unique_file_path(check_file_path:str|Path, randomize_mode:str='i', create_dir:bool=True)->Path:
    """
    Check uniquenes and return a unique file-path
    :param check_file_path: path to check for duplicate
    :param randomize_mode:
    i => incremented integer between prefix and suffix
    r => random string between prefix and suffix
    :param create_dir: to to create the directory on demand
    :return: unique file-path for this directory
    """
    if isinstance(check_file_path, str):
        check_file_path = Path(check_file_path)

    directory = check_file_path.parent

    if not directory.is_dir():
        if create_dir:
            try:
                # recursive
                directory.mkdir(parents=True)
            except:
                raise Exception(f"directory '{directory}' could not be created")
        else:
            raise FileNotFoundError(f"directory '{directory}' not found")

    if check_file_path.is_file():
        suffix = check_file_path.suffix
        prefix = check_file_path.stem
        if randomize_mode == 'i':
            # Variante 1: hochgezählte integer zwischen altem prefix und suffix
            ci = 1
            unique_file_path = directory / f"{prefix}_{ci}{suffix}"
            while unique_file_path.is_file():
                ci += 1
                unique_file_path = directory / f"{prefix}_{ci}{suffix}"
        else:
            # Variante 2: random string, der zwischen dem alten prefix und suffix eingeschoben wird, hier noch mit Unterstrich abgetrennt:
            unique_file_path = Path(tempfile.mktemp(prefix=prefix + '_', suffix=suffix, dir=directory))
    else:
        unique_file_path = check_file_path



    return unique_file_path

def get_features_by_value(vlayer: qgis._core.QgsVectorLayer, field: qgis._core.QgsField | str, value: typing.Any) -> qgis._core.QgsFeatureIterator:
    """Returns all features from layer by query on a single value,
    intended for query dataLyr-Features assigned to specific reference-feature
    sample:
    pol_features = tools.MyTools.get_features_by_value(self.derived_settings.dataLyr,self.derived_settings.dataLyrReferenceField, ref_id)
    leider keine direkte Möglichkeit, die Anzahl der features zu ermitteln, als Workaround muss der QgsFeatureIterator in ein list/dict-Objekt umgewandelt werden
    :param vlayer:
    :param field: queryable-attribute, can be a QgsField or the name of a QgsField
    :param value: any queryable-attribute-value, usually numeric or string, will be used in FilterExpression with 'value'
    """
    # Rev. 2025-01-08
    request = qgis._core.QgsFeatureRequest()
    field_name = field
    if isinstance(field, qgis._core.QgsField):
        field_name = field.name()

    request.setFilterExpression(f'"{field_name}" = \'{value}\'')

    return vlayer.getFeatures(request)



def scan_files(root_path: str|Path, search_patterns='', recursive: bool = True, case_sensitive: bool = False) -> set:
    """Scans directory for files by list of wildcards
    :param root_path: root-directory, type string or Path
    :param search_patterns: seperated list of patterns, f.e. '*.JPG, *.png, *.pdf, *.PDF', not only for extensions 'bla.*', multiple split-characters (comma, semicolon, blank)
    :param recursive: recursiv scan of subdirectories
    :param case_sensitive: consider case in search_patterns '*.JPG' vs. '*.jpg', default: False
    :returns' set of Path (set => unique)
    """
    scan_result = set()

    if isinstance(root_path, str):
        root_path = Path(root_path)

    if root_path.is_dir():

        # parse search_patterns to a list of valid wildcards
        # multiple split-characters
        pattern_set = set()
        for pattern in re.split('[;, ]', search_patterns):
            if pattern:
                pattern_set.add(pattern.strip())

        # special case: *.* => all Files => makes all other patterns superfluous
        if '*.*' in pattern_set:
            pattern_set = set('*.*')

        for pattern in pattern_set:
            if recursive:
                iterator = root_path.rglob(pattern, case_sensitive=case_sensitive)
            else:
                iterator = root_path.glob(pattern, case_sensitive=case_sensitive)

            for scan_file in iterator:
                if scan_file.is_file():
                    # glob/rglob does not differentiate between "regular" files and directories
                    scan_result.add(scan_file)

        return scan_result

    else:
        raise Exception(f"root_path '{root_path}' not found or no directory")


def tool_get_attribute_table_dialogs(iface: qgis.gui.QgisInterface, find_layer_id: str = '', top_level_only:bool = True) -> dict:
    """searches for all attribute-tables in current project
    rather complicated because
    - these dialogs are either docked in iface.mainWindow() or floating as TopLevel-Widget
    - these dialogs must be identified as attribute-tables by special syntaxed objectName(), which hipefully is not going to be changed in furure versions
    :param find_layer_id: optional search attribute-tables for this layer
    :return: dictionary key: layer_id, value: list of attribute_table_widgets
    """
    attribute_table_dialogs = {}

    top_level_dialogs = [wdg for wdg in QtWidgets.QApplication.topLevelWidgets() if isinstance(wdg, QtWidgets.QDialog)]
    for dlg in top_level_dialogs:
        # TopLevel is a QDialog containing QDialog
        top_level_sub_dialogs = dlg.findChildren(QtWidgets.QDialog, options=QtCore.Qt.FindDirectChildrenOnly)
        for sub_dlg in top_level_sub_dialogs:
            if f'QgsAttributeTableDialog/{find_layer_id}' in sub_dlg.objectName():
                found_layer_id = sub_dlg.objectName().replace('QgsAttributeTableDialog/', '')
                if not found_layer_id in attribute_table_dialogs:
                    attribute_table_dialogs[found_layer_id] = []

                attribute_table_dialogs[found_layer_id].append(sub_dlg)

    if not top_level_only:
        main_window_dialogs = iface.mainWindow().findChildren(QtWidgets.QDialog, options=QtCore.Qt.FindChildrenRecursively)
        for dlg in main_window_dialogs:
            if f'QgsAttributeTableDialog/{find_layer_id}' in dlg.objectName():
                found_layer_id = dlg.objectName().replace('QgsAttributeTableDialog/', '')
                if not found_layer_id in attribute_table_dialogs:
                    attribute_table_dialogs[found_layer_id] = []

                attribute_table_dialogs[found_layer_id].append(dlg)

    return attribute_table_dialogs


def show_feature_form(iface: qgis.gui.QgisInterface, vl: qgis._core.QgsVectorLayer, feature_id:int)->qgis._gui.QgsAttributeDialog|None:
    """replacement for iface.openFeatureForm()
    ensures only one feature-form for the same feature
    re-freshes and focusses existing feature-form for this layer/feature
    :param iface:
    :param vl:
    :param feature_id:
    :returns: Attribute-Dialog see https://api.qgis.org/api/classQgsAttributeDialog.html
    or None, if feature exists no more
    """
    # Rev. 2025-06-15
    feature_form = None

    # current "fresh" feature with all intermediate uncommitted/committed edits
    cf = vl.getFeature(feature_id)

    if cf and cf.isValid():
        pre_closed = False
        pre_close_geometry = None

        # ObjectName, used also from iface.openFeatureForm
        my_object_name = f"featureactiondlg:{vl.id()}:{feature_id}"

        # search for QDialog to find both kinds of Dialogs getFeatureForm/openFeatureForm
        # both are direct childs of iface.mainWindow()
        for dialog in iface.mainWindow().findChildren(QtWidgets.QDialog):
            if dialog.objectName() == my_object_name:
                if isinstance(dialog, qgis._gui.QgsAttributeDialog):
                    # opened by getFeatureForm => refreshable
                    atf = dialog.attributeForm()
                    # replace dialog.attributeForm().currentFormFeature() with current feature to show all edits
                    atf.setFeature(cf)
                    # re-open a previous feature-form, "closed" by setHidden(True)
                    dialog.show()
                    # focus:
                    dialog.activateWindow()
                    feature_form = dialog
                else:
                    # QDialog with matching ObjectName found, but no QgsAttributeDialog => via iface.openFeatureForm opened => not refreshable
                    # store geometry to re-open dialog at same position/size
                    pre_close_geometry = dialog.geometry()
                    dialog.close()
                    pre_closed = True

                break

        if not feature_form:
            feature_form = iface.getFeatureForm(vl, cf)
            feature_form.setObjectName(my_object_name)
            # delete QDialog on close instead of setHidden()
            feature_form.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            feature_form.show()
            if pre_closed:
                feature_form.setGeometry(pre_close_geometry)

    return feature_form


def re_open_attribute_tables(iface: qgis.gui.QgisInterface, layer: qgis._core.QgsVectorLayer, new_if_missing:bool):
    """closes, deletes and reopens attribute-tables for a layer
    sort-order, columns-widths and view-mode (table-view/form-view) are conserved
    used for refresh of feature-actions of data- and show-layer on plugin-load and/or settings-change
    :param iface:
    :param layer:
    :param new_if_missing: opens a new attribute-table, if none was found
    """
    attribute_table_dialogs = tool_get_attribute_table_dialogs(iface,layer.id(),True)

    if attribute_table_dialogs:
        for layer_id, dlgs in attribute_table_dialogs.items():
            for dlg in dlgs:
                last_rect = dlg.rect()
                last_x = dlg.mapToGlobal(QtCore.QPoint(0, 0)).x()
                last_y = dlg.mapToGlobal(QtCore.QPoint(0, 0)).y()
                dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
                dlg.close()

                nt = iface.showAttributeTable(layer)
                # minimize-status, resize and reposition only works with the parent(), which is also a QDialog
                nt.parent().setGeometry(last_rect)
                nt.parent().move(last_x, last_y)
    else:
        if new_if_missing:
            iface.showAttributeTable(layer)





def get_mods()->dict:
    """get list of certain keyboard modifiers used for the current event"""
    # Rev. 2025-01-15
    all_mods = {
        'n' : QtCore.Qt.NoModifier,
        's': QtCore.Qt.ShiftModifier,
        'c' : QtCore.Qt.ControlModifier,
        'a' :  QtCore.Qt.AltModifier,# on Linux: move window
        'm' : QtCore.Qt.MetaModifier,# will open StartMenu after release
    }

    return_value = {}
    for check_mod in all_mods:
        mod = all_mods.get(check_mod)
        if mod == QtCore.Qt.NoModifier:
            # binärer Sonderfall für NoModifier (int 0, binär 00000):
            # 11111 & 00000 = 00000 bool False
            # 00000 & 00000 = 00000 bool auch False !
            # => auf Gleicheit checken
            # 00000 == 00000 ? True
            return_value[check_mod] = bool(QtWidgets.QApplication.keyboardModifiers() == mod)
        else:
            # binärer Regelfall für alle anderen (check auf mindestens ein an gleicher Position gesetztes Einzelbit):
            # 10011 & 00010 = 00010 => bool True
            return_value[check_mod] = bool(QtWidgets.QApplication.keyboardModifiers() & mod)
    return return_value

def check_mods(check_mods: str = ''):
    """checks combination of keyboard-modifier
    Combinations must be checked before singles!

    Sample:
    .. code-block:: text

        if check_mods():
            # no modifiers
            pass
        elif check_mods('cs'):
            # ctrl
            pass
        elif check_mods('s'):
            # shift
            pass
        elif check_mods('c'):
            # ctrl
            pass
        else:
            # anything else
            pass

    :param check_mods: string with chars 'n' (NoModifier) 's' (ShiftModifier) 'c' (ControlModifier) 'a' (AltModifier) 'm' (MetaModifier) or empty (=='n', NoModifier) and '+' (and) or '|' (or) for combinator (default '+' and)
    """
    modifiers = get_mods()

    combinator = 'or' if '|' in check_mods else 'and'

    check_mods = check_mods.replace('+','')
    check_mods = check_mods.replace('|', '')

    if check_mods == '':
        check_mods = 'n'


    if combinator == 'and':
        for check_mod in check_mods:
            if check_mod in modifiers:
                if not modifiers.get(check_mod):
                    return False
            else:
                raise NotImplementedError(f"keyboardModifier '{check_mod}' not implemented!")
        # all checks done, no return so far
        return True

    else:
        for check_mod in check_mods:
            if check_mod in modifiers:
                if modifiers.get(check_mod):
                    # one of the modifiers was pressed!
                    return True
            else:
                raise NotImplementedError(f"keyboardModifier '{check_mod}' not implemented!")

    return False


# log function-usages, see debug_log
# 0 => no log
# 1 => log to console
# 2 => log to console and file (helpfully for QGis-crash-debugging)


# global counter-variable used in debug_log
debug_log_ctr = 0
def debug_log(*args,**kwargs):
    """quicky for debugging to console or file
    outputs counter, function, file and line where the debug_log-function was called
    :param args: any number of debug-objects, appended stringified
    :param kwargs: any number of keyword-objects, key prepended to __str__()-stringified output
    """
    global debug_log_ctr

    debug_log_ctr += 1

    path = Path(__file__)
    plugin_folder = str(path.parent.parent.absolute())
    frame = sys._getframe(0)
    fc = 0
    while frame:
        if fc == 1:
            # 0 => this function itself
            # 1 => the function which called this function
            file = os.path.realpath(frame.f_code.co_filename)
            stripped_file = file.replace(plugin_folder, ".")
            log_string = f"{debug_log_ctr}:\t{frame.f_code.co_name}\t{stripped_file}\t#{frame.f_lineno}"

            if args:
                # multiple => each one in new line
                for log_obj in args:
                    log_string += f"\n\t'{str(log_obj)}'"

            if kwargs:
                for key in kwargs:
                    log_string += f"\n\t'{str(key)}'\t'{str(kwargs[key])}'"

            print(log_string)
            # # additionally write to log-file:
            # log_file_name = 'FileSync.log'
            # log_file_path = os.path.join(plugin_folder, log_file_name)
            # with open(log_file_path, "a+", encoding='utf-8') as f:
            #     # prepend with date-time and append to log-file
            #     d_now = datetime.now()
            #     str_now = d_now.strftime('%Y-%m-%d %H:%M:%S')
            #     f.write('\n' + str_now + '\n' + log_string)

            return

        frame = frame.f_back
        fc += 1