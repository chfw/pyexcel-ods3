"""
    pyexcel_ods3.odsr
    ~~~~~~~~~~~~~~~~~~~

    ods reader

    :copyright: (c)  2015-2022 by Onni Software Ltd. & its contributors
    :license: New BSD License
"""
from io import BytesIO

import ezodf
import pyexcel_io.service as service
from pyexcel_io.plugin_api import ISheet, IReader, NamedContent


class ODSSheet(ISheet):
    """ODS sheet representation"""

    def __init__(self, sheet, auto_detect_int=True):
        self.auto_detect_int = auto_detect_int
        self.ods_sheet = sheet

    def row_iterator(self):
        """
        Number of rows in the xls sheet
        """
        return range(self.ods_sheet.nrows())

    def column_iterator(self, row):
        """
        Number of columns in the xls sheet
        """
        for column in range(self.ods_sheet.ncols()):
            yield self.cell_value(row, column)

    def cell_value(self, row, column):
        cell = self.ods_sheet.get_cell((row, column))
        cell_type = cell.value_type
        ret = None
        if cell_type == "currency":
            cell_value = cell.value
            if service.has_no_digits_in_float(cell_value):
                cell_value = int(cell_value)

            if cell.currency is None:
                ret = str(cell_value)
            else:
                ret = str(cell_value) + " " + cell.currency
        elif cell_type in service.ODS_FORMAT_CONVERSION:
            value = cell.value
            n_value = service.VALUE_CONVERTERS[cell_type](value)
            if cell_type == "float" and self.auto_detect_int:
                if service.has_no_digits_in_float(n_value):
                    n_value = int(n_value)
            ret = n_value
        else:
            if cell.value is None:
                ret = ""
            else:
                ret = cell.value
        return ret


class ODSBook(IReader):
    def __init__(self, file_alike_object, file_type, **keywords):
        self.ods_book = ezodf.opendoc(file_alike_object)
        self._keywords = keywords
        self.content_array = [
            NamedContent(sheet.name, sheet) for sheet in self.ods_book.sheets
        ]

    def read_sheet(self, native_sheet_index):
        native_sheet = self.content_array[native_sheet_index].payload
        sheet = ODSSheet(native_sheet, **self._keywords)
        return sheet

    def close(self):
        self.ods_book = None


class ODSBookInContent(ODSBook):
    """
    Open xlsx as read only mode
    """

    def __init__(self, file_content, file_type, **keywords):
        io = BytesIO(file_content)
        super().__init__(io, file_type, **keywords)
