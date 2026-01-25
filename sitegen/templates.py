from jinja2 import Template
from typing import Final

PAGE_FALLBACK: Final[Template] = Template(
    "<html lang=\"en\">"
    "<head>"
        "<title>{{page.title|striptags}}</title>"
    "</head>"
    "<body>"
        "<h1>{{page.title}}</h1>"
        "<div style=\"float:right\">{{page.table_of_contents}}</div>"
        "<p>Last Modified: {{page.modified.strftime(\"%d %b %y\")}}</p>"
        "{{page.html}}"
    "</body>"
    "</html>"
)

RSS_FALLBACK: Final[Template] = Template(
    "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
    "<rss version=\"2.0\">"
    "<channel>"
        "<title>{{ site.title|default(\"Feed for itsdanjc.com\") }}</title>"
        "<link>{{ site.url|default(\"https://itsdanjc.com/\") }}</link>"
        "<description>{{ site.description|default(\"New entries on itsdanjc.com\") }}</description>"
        "<lastBuildDate>{{ now.strftime('%a, %d %b %Y %H:%M:%S GMT') }}</lastBuildDate>"
        "{% for page in tree %}"
        "<item>"
            "<title>"
                "<![CDATA[ {{ page.title }} ]]>"
            "</title>"
            "<description>"
                "<![CDATA["
                    "{% if page.cover_image %}"
                        "<img src=\"{{ page.cover_image }}\" />"
                    "{% endif %}"
                    "{{ page.html }}"
                "]]>"
            "</description>"
            "<link>{{ page.url }}</link>"
            "<guid isPermaLink=\"true\">{{ page.url }}</guid>"
        "</item>"
        "{% endfor %}"
    "</channel>"
    "</rss>"
)

SITEMAP_FALLBACK: Final[Template] = Template(
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    "<urlset xmlns=\"https://www.sitemaps.org/schemas/sitemap/0.9\">"
        "{% for page in tree %}"
        "<url>"
            "<loc>{{ page.url }}</loc>"
            "<lastmod>{{ page.modified.isoformat() }}</lastmod>"
        "</url>"
        "{% endfor %}"
    "</urlset>"
)


PAGE_FALLBACK.name = f"{__name__}:PAGE_FALLBACK"
RSS_FALLBACK.name = f"{__name__}:RSS_FALLBACK"
SITEMAP_FALLBACK.name = f"{__name__}:SITEMAP_FALLBACK"
