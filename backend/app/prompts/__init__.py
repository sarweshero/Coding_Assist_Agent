from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


_PROMPT_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent)),
    autoescape=select_autoescape(["j2", "jinja"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get_template(name: str):
    return _PROMPT_ENV.get_template(name)
