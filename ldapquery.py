import re

import ldap

QA = 'qa'
DEV = 'dev'
CEE = 'cee'
NON_RH = 'non_rh'
UNKNOWN_RH = 'unknown_rh'
EX_RH = 'ex_rh'

RE_CEE = re.compile(r'cn=cee-[^,]*-list,')


class LdapQuerier:

    _INSTANCE = None
    BASE = "ou=users,dc=redhat,dc=com"
    _CACHE = {}

    @classmethod
    def get_instance(cls):
        if not cls._INSTANCE:
            raise Exception("LDAP not initialized")

        return cls._INSTANCE

    def __init__(self, ldap_server):
        self._ldap_server = ldap_server
        self._connection = None

        self.__class__._INSTANCE = self

    def connect(self):
        self._connection = ldap.initialize(self._ldap_server)

    def _query_person(self, uid, depth=3):
        depth -= 1

        if depth == 0:
            raise Exception("Can't talk to the server")

        try:
            try:
                return self._CACHE[uid]
            except KeyError:
                self._CACHE[uid] = self._connection.search_s(
                    self.BASE,
                    ldap.SCOPE_SUBTREE,
                    'uid=%s' % uid,
                    ['memberOf', 'rhatJobRole'])[0][1]
        except ldap.SERVER_DOWN:
            self.connect()
            return self._query_person(uid, depth)
        except IndexError:
            self._CACHE[uid] = {'rhatJobRole': [b'nonRH'], 'memberOf': []}

        return self._CACHE[uid]

    def get_role(self, email):
        if "@redhat.com" not in email:
            return NON_RH


        uid = email.split('@')[0]
        result = self._query_person(uid)

        if 'rhatJobRole' not in result:
            # Not all supports have rhatJobRole
            for cn in result['memberOf']:
                if RE_CEE.match(cn.decode('utf-8')):
                    return CEE
            else:
                return UNKNOWN_RH

        rhat_role = result['rhatJobRole'][0].decode('utf-8')
        if rhat_role == 'Engineer':
            for cn in result['memberOf']:
                if RE_CEE.match(cn.decode('utf-8')):
                    return CEE
            else:
                return DEV
        elif rhat_role == 'Tester':
            return QA
        elif rhat_role == 'nonRH':
            return EX_RH

        return UNKNOWN_RH
