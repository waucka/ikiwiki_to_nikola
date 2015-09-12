## Nikola ikiwiki importer

This plugin will import posts from an ikiwiki blog.

Yeah...just copy import\_ikiwiki.plugin and import\_ikiwiki.py to your nikola plugins directory.

When/If I get this into the nikola plugins repo, you will be able to do this:

    $ nikola plugin -i import_ikiwiki


To use it:

    $ nikola import_ikiwiki path_to_ikiwiki_posts_directory

Or:

    $ nikola import_ikiwiki -o output_directory path_to_ikiwiki_posts_directory

By default, it uses `./posts` as the output directory.  The Markdown compiler MUST be installed and set up!  This plugin only translates ikiwiki-specific syntax to more standard Markdown; it will not convert Markdown to rst or anything like that.

## How does it work?

It will interpret `[[!meta title="whatever"]]` and `[[!tag foo bar]]` (assuming they're on separate lines), use the file's name as the slug, and use the file's modification time as the post time.  All this metadata will be inserted into the Nikola posts.

It's kind of rough, but it worked for my blog.

The following ikiwiki tags will be translated to more standard syntax:

* `[[!img]]` (including alt text and size; the latter causes the tag to be translated to raw HTML)
* `[[!format <syntax> "whatever"]]` (it will silently convert to plain monospaced text if syntax=sh, otherwise it requests user intervention)
* `[[link text|some url]]` (becomes `\[link text\]\(some url\)`)

## License

Copyright © 2015 Alexander Wauck

Distributed under the MIT License.
