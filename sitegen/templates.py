from jinja2 import Template
from typing import Final

BLANK_PAGE_DEFAULT: Final[str] = "# {heading}\n{body}"
DEFAULT_PAGE_TEMPLATE: Final[Template] = Template(
    """<html>
    <head>
    </head>
    <body>
    <h1>{{page.get_title()|safe}}</h1>
    <p>Last Modified: 
    {{page.context.source_path_lastmod.strftime(\"%d %b %y\")}}
    </p>
    {{page.to_html()|safe}}
    </body>
    </html>"""
)