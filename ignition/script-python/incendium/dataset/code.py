"""Dataset module."""

from __future__ import unicode_literals

__all__ = ["from_list_of_dicts", "to_json", "to_jsonobject", "to_xml"]

import system.dataset
import system.date
from com.inductiveautomation.ignition.common import Dataset
from java.util import Date


class _NanoXML(object):
    def __init__(self, root="root", indent="\t"):
        """Nano XML initializer.

        Args:
            root (str): The value of the XML root element.
            indent (str): Character(s) used for indentation.
        """
        super(_NanoXML, self).__init__()
        self.root = root
        self.indent = indent
        self._new_line = "\n"
        self._output = "<{root}>{new_line}".format(
            root=self.root, new_line=self._new_line
        )

    def add_element(self, name):
        """Add an element to the XML document.

        Args:
            name (str): The name of the element.
        """
        self._output += "{indent}<{name}>{new_line}".format(
            indent=self.indent, name=name, new_line=self._new_line
        )

    def add_sub_element(self, name, value):
        """Add a sub element to an element.

        Args:
            name (str): The name of the sub element.
            value (object): The value of the sub element.
        """
        self._output += "{indent}<{name}>{value}</{name}>{new_line}".format(
            indent=self.indent * 2,
            value=value,
            new_line=self._new_line,
            name=name,
        )

    def close_element(self, name):
        """Close element.

        Args:
            name (str): The name of the element.
        """
        self._output += "{indent}</{name}>{new_line}".format(
            indent=self.indent, name=name, new_line=self._new_line
        )

    def to_string(self):
        """Return the string representation of the XML document.

        Returns:
            str: The string representation of the XML document.
        """
        self._output += "</{}>".format(self.root)
        return self._output


def _format_object(obj):
    """Format the value to be properly represented in JSON.

    Args:
        obj (object): The value to format.
        header (str): Column name used for nested Datasets.

    Returns:
        str: The string representation of the value.
    """
    _obj = obj
    if isinstance(obj, Dataset):
        _obj = _to_jsonobject(obj)
    return _obj


def _format_value(obj, header=""):
    """Format the value to be properly represented in JSON.

    Args:
        obj (object): The value to format.
        header (str): Column name used for nested Datasets.

    Returns:
        str: The string representation of the value.
    """
    _obj = ""
    if obj is None:
        _obj = "null"
    elif isinstance(obj, basestring):
        _obj = '"{}"'.format(obj)
    elif isinstance(obj, Date):
        _obj = '"{}"'.format(system.date.format(obj, "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"))
    elif isinstance(obj, Dataset):
        _obj = _to_json(obj, header, False)
    else:
        _obj = "{!r}".format(obj)
    return _obj


def _to_json(dataset, root, is_root=True):
    """Return a string JSON representation of the Dataset.

    Private function.

    Args:
        dataset (Dataset): The input dataset.
        root (str): The value of the header.
        is_root (bool): True if we are at the root, False otherwise.
            Optional.

    Returns:
        str: The string JSON representation of the dataset.
    """
    headers = dataset.getColumnNames()
    columns = dataset.getColumnCount()
    rows = dataset.getRowCount()
    data = system.dataset.toPyDataSet(dataset)
    ret_str = ("{" if is_root and root is not None else "") + (
        '"{}":['.format(root) if root is not None else "["
    )
    col_count = 0

    for row_count, row in enumerate(data, start=1):
        ret_str += "{"
        for header in headers:
            col_count += 1
            val = _format_value(row[header], header)
            comma = "," if col_count < columns else ""
            if isinstance(row[header], Dataset):
                ret_str += "{}{}".format(val, comma)
            else:
                ret_str += '"{}":{}{}'.format(header, val, comma)
        ret_str += "{}{}".format("}", "," if row_count < rows else "")
        col_count = 0
    ret_str += "]"
    ret_str += "}" if is_root and root is not None else ""

    return ret_str


def _to_jsonobject(dataset):
    """Convert a Dataset into a Python list of dictionaries.

    Args:
        dataset (Dataset): The input dataset.

    Returns:
        list[dict]: The Dataset as a Python object.
    """
    data = []
    headers = dataset.getColumnNames()
    row_count = dataset.getRowCount()

    for i in range(row_count):
        row_dict = {
            header: _format_object(dataset.getValueAt(i, header)) for header in headers
        }
        data.append(row_dict)

    return data


def from_list_of_dicts(list_of_dicts):
    """Safely convert a list of Python dictionaries into a Dataset.

    Args:
        list_of_dicts (list[dict]): The list of dictionaries.

    Returns:
        Dataset: A Dataset representation of the list of dictionaries.
    """
    keys_set = set()
    headers = list(keys_set.union(*(d.keys() for d in list_of_dicts)))
    data = []
    for dict_ in list_of_dicts:
        row = []
        for header in headers:
            if header in dict_.keys():
                row.append(dict_[header])
            else:
                row.append(None)
        data.append(row)
    return system.dataset.toDataSet(headers, data)


def to_json(dataset, root=None):
    """Return a string JSON representation of the Dataset.

    Args:
        dataset (Dataset): The input dataset.
        root (str): The value of the root. Optional.

    Returns:
        str: The string JSON representation of the dataset.
    """
    return _to_json(dataset, root)


def to_jsonobject(dataset):
    """Convert a Dataset into a Python list of dictionaries.

    Args:
        dataset (Dataset): The input dataset.

    Returns:
        list[dict]: The Dataset as a Python object.
    """
    return _to_jsonobject(dataset)


def to_xml(dataset, root="root", element="row", indent="\t"):
    r"""Return a string XML representation of the Dataset.

    Args:
        dataset (Dataset): The input dataset.
        root (str): The value of the root. If not provided, it defaults
            to "root". Optional.
        element (str): The value of the row. If not provided, it
            defaults to "row". Optional.
        indent (str): Current indentation. If not provided, it defaults
            to "\t". Optional.

    Returns:
        str: The string XML representation of the dataset.
    """
    headers = dataset.getColumnNames()
    row_count = dataset.getRowCount()
    xml = _NanoXML(root, indent)

    for i in range(row_count):
        xml.add_element(element)
        for header in headers:
            xml.add_sub_element(header, dataset.getValueAt(i, header))
        xml.close_element(element)

    return xml.to_string()
