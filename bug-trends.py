#!/usr/local/bin/python3

import abc
import argparse
import datetime
import json
import re
import sys

import bugzilla

DEFAULT_BZ_URL = "https://bugzilla.redhat.com/xmlrpc.cgi"
SHALE_RE = re.compile(r"^.*shale:\"(?P<shale>{[^\r\n]*})\"")

QUERY = {
    'bug_status': '__open__',
    'chfield': '[Bug creation]',
    'chfieldfrom': '2020-12-01',
    'chfieldto': '2020-12-08',
    'f1': 'cf_internal_whiteboard',
    'list_id': '11597024',
    'o1': 'substring',
    'product': 'Red Hat OpenStack',
    'query_format': 'advanced',
    'v1': 'Squad:OVN',
    "include_fields": [
        "id", "summary", "reporter", "qa_contact", "external_bugs"],

}


class Bug:
    def __init__(self, bug):
        self._bug = bug
        self._customer_tickets = None
        self._shale = None

    @property
    def customer_tickets(self):
        if self._customer_tickets is None:
            self._customer_tickets = [
                ticket for ticket in self._bug.external_bugs
                if ticket['type']['type'] == 'SFDC']
        return self._customer_tickets

    @property
    def has_customer_ticket(self):
        return bool(self.customer_tickets)

    @property
    def shale(self):
        if self._shale is None:
            match = SHALE_RE.match(self._bug.devel_whiteboard)
            if match:
                self._shale = json.loads(
                    match.group("shale").replace("'", '"'))
            else:
                self._shale = {}
        return self._shale

    @property
    def was_escalated(self):
        return self.shale.get('escalated', 'no') == 'yes'

    def __getattr__(self, name):
        return getattr(self._bug, name)

    def __repr__(self):
        return self._bug.__repr__()

    def __str__(self):
        return self._bug.__str__()


class Result(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, field_names):
        pass

    @abc.abstractmethod
    def add_row(self, row):
        pass

    @abc.abstractmethod
    def print(self):
        pass


class CSVResult(Result):
    def __init__(self, field_names):
        import csv
        import io

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

    def __init__(self, field_names):
        import prettytable

        self._table = prettytable.PrettyTable(field_names=field_names)

    def add_row(self, row):
        self._table.add_row(row)

    def print(self):
        print(self._table)


RESULT_FORMAT_CLASS = {
    "csv": CSVResult,
    "table": TableResult,
}


def get_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-k', "--apikey", help="The Bugzilla API key", type=str, required=True)
    parser.add_argument(
        '-u', "--url", help="The Bugzilla XMLRPC API URL", type=str, 
        default=DEFAULT_BZ_URL)
    parser.add_argument(
        '-s', "--startdate", help="Starting date", type=str,
        default=str(datetime.datetime.now().date()))
    parser.add_argument(
        '-w', "--weeks", help="How many weeks to show", type=int, default=1)
    parser.add_argument(
        '-f', "--format", help="Output format", choices=["csv", "table"],
        default="table")
    return parser.parse_args()


def main():
    args = get_opts()
    result = RESULT_FORMAT_CLASS[args.format](
        field_names=[
            "Week",
            "Bugs reported",
#            "Customer bugs",
#            "QE bugs",
#            "Bugs triaged",
#            "Bugs closed",
        ])

    try:
        bzapi = bugzilla.Bugzilla(args.url, api_key=args.apikey)
    except Exception:
        print(e)
        sys.exit(1)

    bzapi.bug_autorefresh = True

    start_date = datetime.datetime.strptime(args.startdate, '%Y-%m-%d')

    import ipdb; ipdb.set_trace()
    for i in range(args.weeks):
        end_date = start_date + datetime.timedelta(weeks=1)
        query = QUERY.copy()
        query.update({
            'chfieldfrom': str(start_date.date()),
            'chfieldto': str(end_date.date())})

        bugs = [Bug(bug) for bug in bzapi.query(query)]
        result.add_row(["%s" % start_date.date(), len(bugs)])
        start_date = end_date

    result.print()


if __name__ == "__main__":
    main()
