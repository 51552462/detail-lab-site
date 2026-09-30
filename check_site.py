"""Check links, IDs and inline JavaScript before publishing the static site."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicates: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.scripts: list[str] = []
        self._inline = False
        self._script: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            identifier = values["id"]
            if identifier in self.ids:
                self.duplicates.append(identifier)
            self.ids.add(identifier)
        if tag in ("a", "link") and values.get("href"):
            self.links.append(("href", values["href"]))
        if tag in ("img", "script") and values.get("src"):
            self.links.append(("src", values["src"]))
        if tag == "script" and not values.get("src") and not values.get("type", "").startswith("application/"):
            self._inline = True
            self._script = []

    def handle_data(self, data: str) -> None:
        if self._inline:
            self._script.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inline:
            self.scripts.append("".join(self._script))
            self._inline = False


def main() -> int:
    pages = {}
    problems = []
    for path in sorted(ROOT.glob("*.html")):
        page = Page()
        page.feed(path.read_text(encoding="utf-8"))
        pages[path] = page
        problems.extend(f"{path.name}: duplicate id #{item}" for item in page.duplicates)

    with TemporaryDirectory() as directory:
        for path, page in pages.items():
            for index, code in enumerate(page.scripts, 1):
                if not code.strip():
                    continue
                script = Path(directory) / f"{path.stem}-{index}.js"
                script.write_text(code, encoding="utf-8")
                result = run(["node", "--check", str(script)], capture_output=True, text=True, check=False)
                if result.returncode:
                    problems.append(f"{path.name}: inline script {index}: {result.stderr.strip()}")

    for path, page in pages.items():
        for attr, link in page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or link.startswith(("//", "#")):
                if not parsed.path and parsed.fragment and parsed.fragment not in page.ids:
                    problems.append(f"{path.name}: missing local anchor #{parsed.fragment}")
                continue
            destination = unquote(parsed.path)
            target = ROOT / destination.lstrip("/") if destination.startswith("/") else path.parent / destination
            if destination == "" or destination.endswith("/"):
                target /= "index.html"
            target = target.resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                problems.append(f"{path.name}: missing {attr} target {link}")
            elif parsed.fragment and target in pages and parsed.fragment not in pages[target].ids:
                problems.append(f"{path.name}: missing anchor {link}")

    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(pages)} HTML pages; local links, anchors, IDs and inline JS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
