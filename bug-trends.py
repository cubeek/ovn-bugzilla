#!/usr/local/bin/python3

import argparse
import datetime
import json
import re
import sys

import bugzilla

import formats
import ldapquery

DEFAULT_LDAP_SERVER = "ldap://ldap.corp.redhat.com"
DEFAULT_BZ_URL = "https://bugzilla.redhat.com/xmlrpc.cgi"
SHALE_RE = re.compile(r"^.*shale:\"?(?P<shale>{[^\r\n]*})")

QUERY = {
#    'bug_status': '__open__',
    'chfield': '[Bug creation]',
    'chfieldfrom': '2020-12-01',
    'chfieldto': '2020-12-08',
    'f1': 'cf_internal_whiteboard',
    'o1': 'substring',
    'product': 'Red Hat OpenStack',
    'query_format': 'advanced',
    "include_fields": [
        "id", "summary", "creator", "external_bugs",
        "cf_devel_whiteboard"],
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
    def shale(self):
        if self._shale is None:
            match = SHALE_RE.match(self._bug.devel_whiteboard)
            if match:
                try:
                    self._shale = json.loads(
                        match.group("shale").replace("'", '"'))
                except json.decoder.JSONDecodeError:
                    self._shale = {}
            else:
                self._shale = {}
        return self._shale

    @property
    def was_escalated(self):
        return self.shale.get('escalated', 'no') == 'yes'

    @property
    def reported_by(self):
        querier = ldapquery.LdapQuerier.get_instance()

        try:
            return querier.get_role(self.creator)
        except AttributeError as e:
            import ipdb; ipdb.set_trace()

    def __getattr__(self, name):
        return getattr(self._bug, name)

    def __repr__(self):
        return self._bug.__repr__()

    def __str__(self):
        return self._bug.__str__()


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
    parser.add_argument(
        '--squad', help="The Network squad", type=str, default="OVN")
    return parser.parse_args()


def process_bugs(start_date, result, bugs):
    date = "%s" % start_date.date()
    escalated = 0
    reporters = {
        ldapquery.QA: 0,
        ldapquery.DEV: 0,
        ldapquery.CEE: 0,
        ldapquery.UNKNOWN_RH: 0,
        ldapquery.NON_RH: 0,
        ldapquery.EX_RH: 0,
    }

    for bug in bugs:
        reporters[bug.reported_by] += 1
        if bug.was_escalated:
            escalated += 1
    result.add_row(
        [date, len(bugs),
         reporters[ldapquery.DEV],
         reporters[ldapquery.QA],
         reporters[ldapquery.CEE],
         reporters[ldapquery.UNKNOWN_RH],
         reporters[ldapquery.EX_RH],
         reporters[ldapquery.NON_RH],
         escalated,
    ])


def main():
    args = get_opts()
    result = formats.get(args.format)(
        field_names=[
            "Week",
            "Bugs reported",
            "Dev reported",
            "QE reported",
            "Support bugs",
            "Other RH",
            "Ex-RH",
            "Out of RH",
            "Escalated bugs",
        ])

    QUERY['v1'] = "Squad:%s" % args.squad

    # initalize LDAP
    querier = ldapquery.LdapQuerier(DEFAULT_LDAP_SERVER)
    querier.connect()

    try:
        bzapi = bugzilla.Bugzilla(args.url, api_key=args.apikey)
    except Exception:
        print(e)
        sys.exit(1)

    #bzapi.bug_autorefresh = True

    start_date = datetime.datetime.strptime(args.startdate, '%Y-%m-%d')

    for i in range(args.weeks):
        end_date = start_date + datetime.timedelta(weeks=1)
        query = QUERY.copy()
        query.update({
            'chfieldfrom': str(start_date.date()),
            'chfieldto': str(end_date.date())})

        bugs = [Bug(bug) for bug in bzapi.query(query)]
        process_bugs(start_date, result, bugs)
        start_date = end_date

    result.print()


if __name__ == "__main__":
    main()
