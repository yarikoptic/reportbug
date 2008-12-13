# $Id: test_hiermatch.py,v 1.1.1.1 2004/02/05 04:29:08 lawrencc Exp $

import hiermatch as hier

def test_list():
    import sys
    a = file(sys.argv[0]).readlines()
    b = hier.grep_list(a, '\[.*\]')
    for i in b:
        print a[i].rstrip()
    print '*'*40
    c = hier.grep_list(a, 'print', b)
    for i in c:
        print a[i].rstrip()


def test_hier():
    import sys
    a = file(sys.argv[0]).readlines()
    b = [(1, a)]
    c = hier.egrep_hierarchy(b, 'print', )
    print c
    for i in range(len(c)):
        for k in c[i]:
            print b[i][1][k].rstrip()
    d = hier.egrep_hierarchy(b, '\[.*\]', c)
    print d
    for i in range(len(d)):
        for k in d[i]:
            print b[i][1][k].rstrip()

def test_mhier():
    import sys
    a = file(sys.argv[0]).readlines()
    b = [(1, a)]
    c = hier.matched_hierarchy(b, 'print', )
    print c
    d = [len(i[1]) for i in c]
    print reduce(lambda x, y: x+y, d)

    

test_mhier()



# vim:ts=8:sw=4:expandtab:

