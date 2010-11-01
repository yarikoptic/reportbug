import unittest2

from reportbug import hiermatch, exceptions

test_strings_list = ['Beautiful is better than ugly.',
                     'Explicit is better than implicit.',
                     'Simple is better than complex.',
                     'Complex is better than complicated.',
                     'Flat is better than nested.',
                     'Sparse is better than dense.']

class TestHiermatch(unittest2.TestCase):

    def test_egrep_list(self):
        res = hiermatch.egrep_list(None, '')
        self.assertIsNone(res)

        with self.assertRaises(exceptions.InvalidRegex):
            matches = hiermatch.egrep_list(test_strings_list, 42)

        matches = hiermatch.egrep_list(test_strings_list, 'better')
        self.assertEqual(len(matches), 6)
