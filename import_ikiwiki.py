# -*- coding: utf-8 -*-

# Copyright © 2015 Alexander Wauck.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Import posts from an ikiwiki blog."""

import os
import re
import sys
import datetime

import dateutil

from nikola.plugin_categories import Command
from nikola import utils
from nikola.plugins.basic_import import ImportMixin

LOGGER = utils.get_logger('import_ikiwiki', utils.STDERR_HANDLER)

def get_date(dt, tz=None, iso8601=False):
    """Return a Nikola date/time stamp.

    dt - datetime:
        the date/time stamp to use

    tz - tzinfo:
        the timezone used

    iso8601 - bool:
        whether to force ISO 8601 dates (instead of locale-specific ones)

    """
    if tz is None:
        tz = dateutil.tz.tzlocal()
    date = now = datetime.datetime.now(tz)
    date = dt
    offset = tz.utcoffset(now)
    offset_sec = (offset.days * 24 * 3600 + offset.seconds)
    offset_hrs = offset_sec // 3600
    offset_min = offset_sec % 3600
    if iso8601:
        tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
    else:
        if offset:
            tz_str = ' UTC{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
        else:
            tz_str = ' UTC'

    return date.strftime('%Y-%m-%d %H:%M:%S') + tz_str

MD_HEADER_BLOCK = """<!-- 
.. title: {title}
.. slug: {slug}
.. date: {date}
.. tags: {tags}
.. category: 
.. link: 
.. description: 
.. type: text
-->
"""

DEFAULT_OUTPUT_EXT = '.md'
IMG_SUPPORTED_ATTRS = {'url', 'alt', 'size'}
JUST_MONOSPACE_SYNTAX = { 'sh', }

title_regex = re.compile(r'\[\[!meta\stitle="(?P<title>[^"]+)"\s*\]\]')
tags_regex = re.compile(r'\[\[!tag\s(?P<tags>(\S+\s?)+)\s*\]\]')
img_regex = re.compile(r'\[\[!img\s(?P<url>\S+)(?P<pairs>(\s\w+="[^"]+")*)\s*\]\]')
link_regex = re.compile(r'\[\[(?P<text>[^|]+)\|(?P<url>\S+)\]\]')
too_liberal_regex = re.compile(r'\[\[(?P<text>[^|]+)\|\|(?P<url>\S+)\]\]')
format_regex = re.compile(r'\[\[!format\s(?P<syntax>\S+)\s+"(?P<content>[^"]+)"\s*\]\]')
generic_regex = re.compile(r'.*\[\[!(?P<name>\w+)\s+.*\]\].*')
filename_regex = re.compile(r'.*\.mdwn$')
whitespace_regex = re.compile(r'\s')
pair_regex = re.compile(r'\s*(?P<key>\w+)="(?P<value>[^"]+)"')

# Set way down below
REPLACE_TAGS = {}

def replace_format_tags(line):
    new_line = line
    err = None
    while True:
        next_match = format_regex.search(new_line)
        if next_match:
            new_line_mod = new_line[:next_match.start()]
            new_line_mod += "`{content}`".format(content=next_match.group('content'))
            if next_match.group('syntax') not in JUST_MONOSPACE_SYNTAX:
                new_line_mod += "<pre>FIXME: syntax={syntax}</pre>".format(syntax=next_match.group('syntax'))
                err = 'WARNING: format tag needs manual intervention!'
            new_line_mod += new_line[next_match.end():]
            new_line = new_line_mod
        else:
            return new_line, err
    return new_line, err

def replace_ikiwiki_links(line, posts_base_path='..'):
    new_line = line
    while True:
        next_match = link_regex.search(new_line)
        if next_match:
            url = next_match.group('url')
            text = next_match.group('text')

            if '/' not in url:
                url = posts_base_path + '/' + url

            # Check for [[foo||url]]
            # ikiwiki ought to reject this, but apparently it doesn't.
            if too_liberal_regex.match(next_match.group(0)):
                url = url[1:]

            new_line_mod = new_line[:next_match.start()]
            new_line_mod += "[{text}]({url})".format(text=text,
                                                     url=url)
            new_line_mod += new_line[next_match.end():]
            new_line = new_line_mod
        else:
            # print("No ikiwiki links in:\n", new_line)
            return new_line
    return new_line

def parse_img(line):
    matches = img_regex.match(line)
    if not matches:
        #print("{0} didn't match for img".format(line))
        return None
    # print("img: ", line.rstrip())
    img = { "url": matches.group('url') }
    if len(matches.group('pairs')) > 0:
        # print("Pairs: \"{0}\"".format(matches.group('pairs')))
        pairs_list = whitespace_regex.split(matches.group('pairs'))
        for pair_match in pair_regex.finditer(matches.group('pairs')):
            key = pair_match.group('key')
            value = pair_match.group('value')
            img[key] = value
    if not img['url'].startswith('http://') and not img['url'].startswith('https://'):
        img['url'] = '/' + img['url']
    return img

def img_is_supported(img):
    for attr in img.keys():
        if attr not in IMG_SUPPORTED_ATTRS:
            return False
    return True

def fix_tag(tag):
    if tag in REPLACE_TAGS:
        return REPLACE_TAGS[tag]
    return tag

class Converter(object):
    def __init__(self, filename, contents):
        self.filename = filename
        self.contents = contents
        self.line_num = None

    def _error(msg):
        print("[{filename}:{line_num}] {msg}".format(filename=self.filename,
                                                     line_num=self.line_num,
                                                     msg=msg),
              file=sys.stderr)

    def convert(self, output_stream, slug, default_title, date):
        title = None
        tags = []
        lines = self.contents.split('\n')
        for line in lines:
            matches = title_regex.match(line)
            if matches:
                title = matches.group('title')
                continue
            matches = tags_regex.match(line)
            if matches:
                tags_str = matches.group('tags')
                tags = [fix_tag(tag) for tag in tags_str.split(' ')]
                continue
            # img = parse_img(line)
            # if img:
            #     print("Image: ", img['url'])
            #     for key in img.keys():
            #         if key != 'url':
            #             print("       {0}: {1}".format(key, img[key]))
        if title is None:
            title = default_title
        # print("Title: ", title)
        # print("Tags: ", ','.join(tags))
        # print("Date: ", date)
        output_stream.write(MD_HEADER_BLOCK.format(title=title,
                                                   slug=slug,
                                                   date=date,
                                                   tags=','.join(tags)))
        output_stream.write('\n')
        for (line_num, line) in enumerate(lines):
            self.line_num = line_num
            if title_regex.match(line) or tags_regex.match(line):
                continue
            line = replace_ikiwiki_links(line)
            line, err = replace_format_tags(line)
            if err:
                self._error(err)
            generic_match = generic_regex.match(line)
            img = parse_img(line)
            if img:
                if img_is_supported(img):
                    if 'alt' not in img:
                        img['alt'] = ''
                    if 'size' not in img:
                        output_stream.write("![{alt}]({url})\n".format(**img))
                    else:
                        output_stream.write('<img src="{url}" alt="{alt}" height="{size}px"></img>\n'.format(**img))
                else:
                    output_stream.write("<pre>FIXME\n{0}\n</pre>\n".format(line))
                    self._error('WARNING: img tag needs manual intervention!')
            elif generic_match:
                    output_stream.write("<pre>FIXME\n{0}\n</pre>\n".format(line))
                    self._error("WARNING: {tagname} tag needs manual intervention!".format(tagname=generic_match.group('name')))
            else:
                output_stream.write(line)
                output_stream.write('\n')


class CommandImportIkiwiki(Command, ImportMixin):
    """Import posts from an ikiwiki blog."""

    name = "import_ikiwiki"
    needs_config = False
    doc_usage = "[options] input_dir"
    doc_purpose = "import posts from an ikiwiki blog"
    cmd_options = ImportMixin.cmd_options + [
        {
            'name': 'overwrite',
            'long': 'overwrite',
            'short': 'w',
            'default': False,
            'type': bool,
            'help': "Overwrite existing posts with the same name",
        },
    ]

    def _execute(self, options, args):
        """Import posts from an ikiwiki blog."""
        # configuration
        overwrite = options.get('overwrite', False)
        output_dir = options.get('output_folder', None)
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), 'posts')

        # args
        input_dir = args[0]

        if 'IKIWIKI_REPLACE_TAGS' in self.site.config:
            global REPLACE_TAGS
            REPLACE_TAGS = self.site.config['IKIWIKI_REPLACE_TAGS']

        try:
            force_iso8601 = self.site.config['FORCE_ISO8601']
        except:
            force_iso8601 = False

        for root, _, files in os.walk(input_dir):
            for filename in files:
                if not filename_regex.match(filename):
                    continue

                (fileroot, ext) = os.path.splitext(filename)
                filepath = os.path.join(root, filename)
                print("Processing ", filepath)


                if 'IKIWIKI_OUTPUT_EXT' in self.site.config:
                    output_ext = self.site.config['IKIWIKI_OUTPUT_EXT']
                else:
                    output_ext = DEFAULT_OUTPUT_EXT
                output_filepath = os.path.join(output_dir, fileroot + output_ext)
                default_title = fileroot.replace('_', ' ')
                stats = os.stat(filepath)
                date = get_date(datetime.datetime.fromtimestamp(stats.st_mtime), iso8601=force_iso8601)

                if os.path.exists(output_filepath) and not overwrite:
                    print("File {output} already exists.  Not overwriting!".format(output=output_filepath),
                          file=sys.stderr)

                with open(filepath, 'rb') as f:
                    contents = f.read().decode('utf-8')

                with open(output_filepath, 'wt') as f:
                    converter = Converter(filename, contents)
                    converter.convert(f, fileroot, default_title, date)
