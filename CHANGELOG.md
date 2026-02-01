# Changelog

## 0.3.0
- Complete rewrite of build classes

## Fixes
- When creating rss and sitemap, it no longer needs to rerender all pages again.
- Exits gracefully when the is no source directory.

## Added
- Caching file index, gives huge performance boost for large sites.

## 0.2.0
### Added
- RSS Feed.
- Sitemap.

### Fixes
- Fixed compatibility with Python > 1.12 - https://github.com/itsdanjc/itsdanjc.com/issues/12.
- Templates not loaded from correct location.

## 0.1.3
### Added
- Added context variable for the current page URL.
- Added fallback template for a page.
- Added fallback template for RSS feed.
- Added fallback template for sitemap.

### Fixes
- Fixed issue where blank page default was not populated.

## 0.1.2
### Added
- Add packaging configurations. Can now be run with `sitegen`.