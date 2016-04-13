"""
    pyexcel.ext.ods3
    ~~~~~~~~~~~~~~~~~~~

    ODS format plugin for pyexcel

    :copyright: (c)  2015-2016 by Onni Software Ltd. & its contributors
    :license: New BSD License
"""
import sys
import datetime
import ezodf

from pyexcel_io.io import get_data as read_data, isstream, store_data as write_data
from pyexcel_io.book import BookReader, BookWriter
from pyexcel_io.sheet import SheetReader, SheetWriter
from pyexcel_io.manager import RWManager

PY2 = sys.version_info[0] == 2
if PY2 and sys.version_info[1] < 7:
    from ordereddict import OrderedDict
else:
    from collections import OrderedDict    


def float_value(value):
    ret = float(value)
    return ret


def date_value(value):
    ret = "invalid"
    try:
        # catch strptime exceptions only
        if len(value) == 10:
            ret = datetime.datetime.strptime(
                value,
                "%Y-%m-%d")
            ret = ret.date()
        elif len(value) == 19:
            ret = datetime.datetime.strptime(
                value,
                "%Y-%m-%dT%H:%M:%S")
        elif len(value) > 19:
            ret = datetime.datetime.strptime(
                value[0:26],
                "%Y-%m-%dT%H:%M:%S.%f")
    except:
        pass
    if ret == "invalid":
        raise Exception("Bad date value %s" % value)
    return ret


def time_value(value):
    hour = int(value[2:4])
    minute = int(value[5:7])
    second = int(value[8:10])
    if hour < 24:
        return datetime.time(hour, minute, second)
    else:
        return datetime.timedelta(hours=hour, minutes=minute, seconds=second)



def boolean_value(value):
    return value


ODS_FORMAT_CONVERSION = {
    "float": float,
    "date": datetime.date,
    "time": datetime.time,
    "boolean": bool,
    "percentage": float,
    "currency": float
}


ODS_WRITE_FORMAT_COVERSION = {
    float: "float",
    int: "float",
    str: "string",
    datetime.date: "date",
    datetime.time: "time",
    datetime.timedelta: "timedelta",
    bool: "boolean"
}


VALUE_CONVERTERS = {
    "float": float_value,
    "date": date_value,
    "time": time_value,
    "boolean": boolean_value,
    "percentage": float_value,
    "currency": float_value
}


VALUE_TOKEN = {
    "float": "value",
    "date": "date-value",
    "time": "time-value",
    "boolean": "boolean-value",
    "percentage": "value",
    "currency": "value"
}


if sys.version_info[0] < 3:
    ODS_WRITE_FORMAT_COVERSION[unicode] = "string"


def _read_cell(cell):
    cell_type = cell.value_type
    ret = None
    if cell_type in ODS_FORMAT_CONVERSION:
        value = cell.value
        n_value = VALUE_CONVERTERS[cell_type](value)
        ret = n_value
    else:
        if cell.value is None:
            ret = ""
        else:
            ret = cell.value
    return ret


class ODSSheet(SheetReader):
    @property
    def name(self):
        return self.native_sheet.name

    def to_array(self):
        """reads a sheet in the sheet dictionary, storing each sheet
        as an array (rows) of arrays (columns)"""
        for row in range(self.native_sheet.nrows()):
            row_data = []
            tmp_row = []
            for cell in self.native_sheet.row(row):
                cell_value = _read_cell(cell)
                tmp_row.append(cell_value)
                if cell_value is not None and cell_value != '':
                    row_data += tmp_row
                    tmp_row = []
            if len(row_data) > 0:
                yield row_data


class ODSBook(BookReader):

    def __init__(self):
        BookReader.__init__(self, 'ods')
        self.native_book = None

    def open(self, file_name, **keywords):
        BookReader.open(self, file_name, **keywords)
        self._load_from_file()

    def open_stream(self, file_stream, **keywords):
        BookReader.open_stream(self, file_stream, **keywords)
        self._load_from_memory()

    def read_sheet_by_name(self, sheet_name):
        rets = [sheet for sheet in self.native_book.sheets if sheet.name == sheet_name]
        if len(rets) == 0:
            raise ValueError("%s cannot be found" % sheet_name)
        elif len(rets) == 1:
            return self._read_sheet(rets[0])
        else:
            raise ValueError(
                "More than 1 sheet named as %s are found" % sheet_name)            
        pass

    def read_sheet_by_index(self, sheet_index):
        sheets = self.native_book.sheets
        length = len(sheets)
        if sheet_index < length:
            return self._read_sheet(sheets[sheet_index])
        else:
            raise IndexError("Index %d of out bound %d." % (sheet_index,
                                                            length))

    def read_all(self):
        result = OrderedDict()
        for sheet in self.native_book.sheets:
            ods_sheet = ODSSheet(sheet)
            result[ods_sheet.name] = ods_sheet.to_array()
        return result
        
    def _read_sheet(self, native_sheet):
        sheet = ODSSheet(native_sheet)
        return {native_sheet.name: sheet.to_array()}


    def _load_from_file(self):
        self.native_book = ezodf.opendoc(self.file_name)

    def _load_from_memory(self):
        self.native_book = ezodf.opendoc(self.file_stream)


class ODSSheetWriter(SheetWriter):
    """
    ODS sheet writer
    """
    def set_sheet_name(self, name):
        self.native_sheet = ezodf.Sheet(name)
        self.current_row = 0

    def set_size(self, size):
        self.native_sheet.reset(size=size)

    def write_row(self, array):
        """
        write a row into the file
        """
        count = 0
        for cell in array:
            value_type = ODS_WRITE_FORMAT_COVERSION[type(cell)]
            if value_type == "time":
                cell = cell.strftime("PT%HH%MM%SS")
            elif value_type == "timedelta":
                hours = cell.days * 24 + cell.seconds // 3600
                minutes = (cell.seconds // 60) % 60
                seconds = cell.seconds % 60
                cell = "PT%02dH%02dM%02dS" % (hours, minutes, seconds)
                value_type = "time"
            self.native_sheet[self.current_row, count].set_value(
                cell,
                value_type=value_type)
            count += 1
        self.current_row += 1

    def close(self):
        """
        This call writes file

        """
        self.native_book.sheets += self.native_sheet


class ODSWriter(BookWriter):
    """
    open document spreadsheet writer

    """
    def __init__(self):
        BookWriter.__init__(self, 'ods')  # in case something will be done
        self.native_book = None

    def open(self, file_name, **keywords):
        BookWriter.open(self, file_name, **keywords)
        self.native_book = ezodf.newdoc(doctype="ods", filename=self.file_alike_object)

    def create_sheet(self, name):
        """
        write a row into the file
        """
        return ODSSheetWriter(self.native_book, None, name)

    def close(self):
        """
        This call writes file

        """
        self.native_book.save()


def save_data(afile, data, file_type=None, **keywords):
    if isstream(afile) and file_type is None:
        file_type = 'ods'
    write_data(afile, data, file_type=file_type, **keywords)


def get_data(afile, file_type=None, **keywords):
    if isstream(afile) and file_type is None:
        file_type = 'ods'
    return read_data(afile, file_type=file_type, **keywords)


RWManager.register_a_reader('ods', ODSBook)
RWManager.register_a_writer('ods', ODSWriter)
RWManager.register_file_type_as_binary_stream('ods')
