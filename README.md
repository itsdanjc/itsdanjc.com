# itsdanjc.com

## Usage

### Building site
```text
$ sitegen build

options:
  -h, --help            Show this help message and exit.
  -f, --force           Force rebuild of all pages.
  -c, --clean           Clear the build directory, then build.
  -d, --dry-run         Run as normal. but don't create build files.
  -r, --site-root PATH  Location of webroot, if not at the current working directory.
  --no-rss              Do not update or create rss feed.
  --no-sitemap          Do not update or create sitemap.  
```

### Show site structure
```text
$ sitegen tree

options:
  -h, --help            Show this help message and exit.
  -i, --reindex         Ignore cache and reindex.
  -f, --format  STRING  Output in this format [tree, url, json].
  -s, --sort    STRING  Sort the result (not available with --format tree) [type, path, lastmod, lastbuild].
  -m, --max    INTEGER  Only return up to this number of entries, can be a performance benefit (not available with --format tree).
  -r, --site-root PATH  Location of webroot, if not at the current working directory.
```
