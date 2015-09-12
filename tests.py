from import_ikiwiki import replace_ikiwiki_links
from import_ikiwiki import replace_format_tags
from import_ikiwiki import get_date, Converter
import unittest
import io
import os
import datetime

class ReplacementTests(unittest.TestCase):
    def test_replace_ikiwiki_links(self):
        line = 'No [old-fashioned links](https://impulse101.org) in here!'
        expected = line
        self.assertEqual(replace_ikiwiki_links(line), expected)

        line = 'Here is a [[link|random_post]] to another post.'
        expected = 'Here is a [link](../random_post) to another post.'
        self.assertEqual(replace_ikiwiki_links(line), expected)

        line = 'Here is a [[link|https://www.google.com]] embedded in some text.'
        expected = 'Here is a [link](https://www.google.com) embedded in some text.'
        self.assertEqual(replace_ikiwiki_links(line), expected)

        line = 'Here is a [[link|https://www.google.com]] embedded in some text.  [[Oh no!|https://reddit.com]]  Here\'s some more!'
        expected = 'Here is a [link](https://www.google.com) embedded in some text.  [Oh no!](https://reddit.com)  Here\'s some more!'
        self.assertEqual(replace_ikiwiki_links(line), expected)

    def test_replace_format_tags(self):
        line = 'Running [[!format sh "postsuper -r ALL"]] should fix it'
        expected = 'Running `postsuper -r ALL` should fix it'
        self.assertEqual(replace_format_tags(line), (expected, None))

        line = 'Running [[!format sh "postsuper -r ALL"]] or [[!format sh "dd if=/dev/zero of=/dev/sda bs=1M"]] should fix it'
        expected = 'Running `postsuper -r ALL` or `dd if=/dev/zero of=/dev/sda bs=1M` should fix it'
        self.assertEqual(replace_format_tags(line), (expected, None))

        line = 'Sadly, no support for [[!format python "print(\'Your favorite language\')"]] unless you want just monospace.'
        expected = 'Sadly, no support for `print(\'Your favorite language\')`'
        expected += '<pre>FIXME: syntax=python</pre>'
        expected +=' unless you want just monospace.'
        result, err = replace_format_tags(line)
        self.assertEqual(result, expected)
        self.assertIsNotNone(err)

    def test_end_to_end(self):
        with open('testcases/ikiwiki_links/test.md', 'rb') as f:
            contents = f.read().decode('utf-8')

        stats = os.stat('testcases/ikiwiki_links/test.md')
        date = get_date(datetime.datetime.fromtimestamp(stats.st_mtime), iso8601=False)

        output = io.StringIO()
        converter = Converter('test.md', contents)
        converter.convert(output, 'linux_pieces_part2', 'SHOULD NOT APPEAR', date)

        with open('testcases/ikiwiki_links/expected.md', 'rb') as f:
            expected = f.read().decode('utf-8')
        old_maxDiff = self.maxDiff
        self.maxDiff = None
        self.assertEqual(output.getvalue(), expected)
        self.maxDiff = old_maxDiff


if __name__ == '__main__':
    unittest.main()
