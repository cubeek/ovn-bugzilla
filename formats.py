
import abc
import json


def get(format_):
    return _FORMATS[format_]


class Result(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, name, field_names):
        pass

    @abc.abstractmethod
    def add_row(self, row):
        pass

    @abc.abstractmethod
    def print(self):
        pass


class CSVResult(Result):
    def __init__(self, name, field_names):
        import csv
        import io

        self.name = name
        self._field_names = field_names
        self._buffer = io.StringIO()
        self._writer = csv.DictWriter(
            self._buffer, fieldnames=self._field_names)

    def add_row(self, row):
        self._writer.writerow(
            {name: value for name, value in zip(self._field_names, row)})

    def print(self):
        print(self._buffer.getvalue())


class TableResult(Result):

    def __init__(self, name, field_names):
        import prettytable

        self.name = name
        self._table = prettytable.PrettyTable(field_names=field_names)

    def add_row(self, row):
        self._table.add_row(row)

    def print(self):
        print(self.name)
        print(self._table)


class JSONResult(Result):
    def __init__(self, name, field_names):
        self.name = name
        self.data = []

        self.field_names = field_names

    def add_row(self, row):
        self.data.append(row)

    def print(self):
        result = {
            'columns': self.field_names,
            'data': self.data,
        }

        print(json.dumps(result))


_FORMATS = {
    'csv': CSVResult,
    'table': TableResult,
    'json': JSONResult,
}
