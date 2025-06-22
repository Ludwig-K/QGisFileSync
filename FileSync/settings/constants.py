#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin FileSync:
* plugin-wide used variables

********************************************************************

* Date                 : 2025-06-11
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

********************************************************************
"""
from enum import IntEnum

# Qt_Roles
# used for storing data in QStandardItemModel, f.e. MyQComboBox, MyQTreeView...
# QStandardItem.setData(value,role) rsp. value = QStandardItem.data(role)
# (Note QListWidgetItem uses setData(role,value))
# the model-items (QtGui.QStandardItem) store data in roles
# Qt uses standard-roles in range 0...255 (DisplayRole => 0, DecorationRole => 1, EditRole => 2, TextAlignmentRole, FontRole, ToolTipRole, ...UserRole => 256)
# additional roles should use integers > UserRole (256),
# each added value inside below IntEnum gets an incremented integer starting with 257
# usage:
# import to python-file via from LinearReferencing.settings.constants import Qt_Roles
# inside these files Qt_Roles is a global variable, access to integer-values via name: Qt_Roles.CUSTOM_SORT, Qt_Roles.REF_FID etc.

# CUSTOM_SORT: used inside MyStandardItem for sort by (numeric) value instead default by Text == DisplayRole, usefull for numerical values, displayed formatted, which should be sorted in numerical instead of alphabetical range
# OPTION_TEXT: MyQComboBox -> role for Wildcard-replacements {0} {1}... in option_text_template, used for the selected option (QLineEdit)
# RETURN_VALUE: universal role, f.e. QgsField inside MyQComboBox in Plugin-layer-field-configuration
Qt_Roles = IntEnum('Qt_Roles', ['CUSTOM_SORT', 'RETURN_VALUE','OPTION_TEXT'], start=257)
