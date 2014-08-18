#!/usr/bin/python

import logging
l = logging.getLogger('ldifmod')
#logging.basicConfig()
#l.setLevel(logging.DEBUG)

class LDIF:
    def __init__(self, lines, load=True, dn_marker='', separator='='):
        self.lines = lines
        self.entries = { }
        self.dn_marker = dn_marker
        self.separator = separator
        self.indexes = { }

        if load:
            self.load_entries()

    def load_entries(self):
        for dn, entry in self.__iter__():
            l.debug('Adding: %s', dn)
            self.entries[dn] = entry

    def __iter__(self):
        last_attr = 'dn'
        entry = { 'dn': [ '' ] }

        for line in self.lines:
            line = line.rstrip()

            if line == '':
                if entry['dn'][0] != '':
                    dn = entry['dn'][0]
                    #del entry['dn']
                    yield dn, entry
                entry = { 'dn': [ '' ] }
                last_attr = 'dn'
                continue

            if entry['dn'][0] == '':
                try:
                    #l.debug('|%s|   |%s|' % (dn_marker, line))
                    if self.dn_marker != '':
                        entry['dn'][0] = line.split(self.dn_marker)[1]
                    else:
                        entry['dn'][0] = line
                    #l.debug('new DN: |%s|', dn)
                except Exception, e: #pylint:disable=W0703
                    l.error('Skipping line: |%s| due to exception %s', line, e)
                continue

            last_attr = self.parse_line(entry, line, last_attr)

        if entry['dn'][0] != '':
            dn = entry['dn'][0]
            #del entry['dn']
            yield dn, entry

    def parse_line(self, entry, line, last_attr):
        try:
            if line[0] == ' ':
                attr_name = last_attr
                entry[last_attr][-1] += line[1:]
            else:
                attr_name, attr_value = line.split(self.separator, 1)

                # handle multi-line LDIF attrs
                if attr_name[-1] == self.separator[0]:
                    attr_name = attr_name[:-1]
                attr_name = attr_name.lower()

                if attr_name not in entry:
                    entry[attr_name] = [ ]
                entry[attr_name].append(attr_value)

            return attr_name
        except Exception:
            l.error('Invalid attribute line: |%s|', line)
            raise
            #return last_attr

    def to_str(self):
        s = [ ]
        for dn in self.entries:
            s.append(dn)
            for attr in self.entries[dn]:
                for val in self.entries[dn][attr]:
                    s.append(attr + '=' + val)
            s.append('')
        return '\n'.join(s)

    # writes out an ldif for modification. Doesn't support multi-val attrs.
    def make_ldifmod(self, f, other):
        for dn in self.entries:
            o = dict(self.entries[dn])
            n = dict(other.entries[dn])

            del o['dn']
            del n['dn']

            adds = list(set(n.keys()) - set(o.keys()))
            deletes = list(set(o.keys()) - set(n.keys()))

            changes = [ ]
            for attr in set(o.keys()) & set(n.keys()):
                if o[attr][0] != n[attr][0]:
                    changes.append(attr)

            if len(adds) + len(deletes) + len(changes) == 0:
                continue

            # print
            f.write('dn: %s\n' % dn)
            f.write('changetype: modify\n')

            for a in adds:
                f.write('add: %s\n%s: %s\n-\n' % (a, a, n[a][0]))

            for a in deletes:
                f.write('delete: %s\n-\n' % a)

            for a in changes:
                f.write('replace: %s\n%s: %s\n-\n' % (a, a, n[a][0]))

            f.write('\n')

    def index(self, attr):
        attr = attr.lower()

        if attr in self.indexes:
            l.debug('Attribute %s is already indexed.', attr)
            return

        self.indexes[attr] = { }
        for entry in self.entries.itervalues():
            if attr not in entry:
                continue

            for v in entry[attr]:
                if v not in self.indexes[attr]:
                    self.indexes[attr][v] = [ ]
                self.indexes[attr][v] = entry

