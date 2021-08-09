#!/usr/local/bin/python3

import argparse
import datetime
import json
import re
import sys
import time

import bugzilla

import formats
import ldapquery

BUG_STATES = ('assigned', 'triaged', 'on_dev', 'post', 'modified', 'on_qa',
              'verified', 'release_pending', 'closed')
DEFAULT_LDAP_SERVER = "ldap://ldap.corp.redhat.com"
DEFAULT_BZ_URL = "https://bugzilla.redhat.com/xmlrpc.cgi"
SHALE_RE = re.compile(r"^.*shale:\"?(?P<shale>{[^\r\n]*})")
QUERY = {
    # 'bug_status': '__open__',
    'chfield': '[Bug creation]',
    'chfieldfrom': '2020-12-01',
    'chfieldto': '2020-12-08',
    'f1': 'cf_internal_whiteboard',
    'o1': 'substring',
    'product': 'Red Hat OpenStack',
    'query_format': 'advanced',
    "include_fields": [
        "id", "summary", "component", "creator", "external_bugs",
        "cf_devel_whiteboard", "product", "creation_time"],
}
SEC_PER_DAY = 86400


class Bug:
    def __init__(self, bug):
        self._bug = bug
        self._customer_tickets = None
        self._shale = None
        self._creation_time = None

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
            # import ipdb; ipdb.set_trace()
            print(e)

    @property
    def creation_time(self):
        if not self._creation_time:
            self._creation_time = datetime.datetime.strptime(
                self._bug.creation_time.value, "%Y%m%dT%H:%M:%S")
        return self._creation_time

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
        '-f', "--format", help="Output format",
        choices=["csv", "table", "json"], default="table")
    parser.add_argument(
        '--squad', help="The Network squad", type=str, default="OVN")
    parser.add_argument(
        '-bz', "--bugzilla", help="The ID of a BZ bug", type=str)

    return parser.parse_args()


def process_by_reporter(result, date, bug_list):
    escalated = 0
    reporters = {
        ldapquery.QA: 0,
        ldapquery.DEV: 0,
        ldapquery.CEE: 0,
        ldapquery.UNKNOWN_RH: 0,
        ldapquery.NON_RH: 0,
        ldapquery.EX_RH: 0,
    }

    for bug in bug_list:
        reporters[bug.reported_by] += 1
        if bug.was_escalated:
            escalated += 1
    result.add_row(
        [date, len(bug_list),
         reporters[ldapquery.DEV],
         reporters[ldapquery.QA],
         reporters[ldapquery.CEE],
         reporters[ldapquery.UNKNOWN_RH],
         reporters[ldapquery.EX_RH],
         reporters[ldapquery.NON_RH],
         escalated])


def process_bugs(format_, bugs):
    by_reporter = formats.get(format_)(
        name='By Reporter',
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

    for date, bug_list in sorted(bugs.items(), key=lambda x: x[0]):
        process_by_reporter(by_reporter, date, bug_list)

    return [by_reporter]


def create_bugs_based_on_report_date(bugs):
    bug_dates = {}
    for bug in bugs:
        bug = Bug(bug)
        monday_date = (
            bug.creation_time - datetime.timedelta(
                days=bug.creation_time.weekday()))
        bug_dates.setdefault(monday_date.strftime("%Y-%m-%d"), []).append(bug)

    return bug_dates


def get_time_epoch(datetime):
    return time.mktime(datetime.timetuple())


def bz_days_to_states(bzapi, bz_id, creation_time):
    """This function returns a dictionary with the days from the bug creation
    to the different states listed on 'BUG_STATES'. If it never got to a state
    it won't appear in the dictionary either.
    """
    creation_time = get_time_epoch(creation_time)
    bz_states_dict = {}
    bz_dates = {}
    history = bzapi.bugs_history_raw(bz_id)['bugs'][0]['history']
    for event in history:
        for change in event['changes']:
            added = change['added'].lower()
            if added in BUG_STATES:
                bz_dates[added] = event['when']
                time_event = get_time_epoch(event['when'])
                bz_states_dict[added] = int(
                    (time_event - creation_time)/SEC_PER_DAY)
    return bz_states_dict


def main():
    args = get_opts()

    QUERY['v1'] = "Squad:%s" % args.squad

    # initalize LDAP
    querier = ldapquery.LdapQuerier(DEFAULT_LDAP_SERVER)
    querier.connect()

    try:
        bzapi = bugzilla.Bugzilla(args.url, api_key=args.apikey)
    except Exception:
        print(e)
        sys.exit(1)

    # bzapi.bug_autorefresh = True

    if args.bugzilla:
        try:
            creation_time = bzapi.getbug(args.bugzilla).creation_time
            bz_states_dict = bz_days_to_states(bzapi, args.bugzilla,
                                               creation_time)
        except Exception as e:
            if hasattr(e, "faultString"):
                print(e.faultString)
            else:
                print(e)
            sys.exit(1)
        for a, b in bz_states_dict.items():
            if a != 'created':
                print("Days to %s: %s" % (a, b))

    else:
        start_date = datetime.datetime.strptime(args.startdate, '%Y-%m-%d')
        end_date = start_date + datetime.timedelta(weeks=args.weeks)

        query = QUERY.copy()
        query.update({
            'chfieldfrom': str(start_date.date()),
            'chfieldto': str(end_date.date())})

        bugs = create_bugs_based_on_report_date(bzapi.query(query))

        reports = process_bugs(args.format, bugs)

        for report in reports:
            report.print()


if __name__ == "__main__":
    main()
