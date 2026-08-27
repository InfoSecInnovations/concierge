import pytest
from shabti_types import ForbiddenUrlError
from ...src.app.functionality.loaders.url_guard import check_url_allowed, same_origin
from ...src.app.functionality.loaders.web import extract_text, scope_patterns

PAGE = """
<html>
  <head>
    <style>body { color: #abcdef; }</style>
    <script>function trackVisitor() { return jQuery.ajax("/beacon"); }</script>
  </head>
  <body>
    <nav><a href="/">Home</a><a href="/lessons/">Lessons</a></nav>
    <main>
      <h1>Countries of the World</h1>
      <p>A single page that lists every country, with its capital and population.</p>
      <table>
        <tr><td>Andorra</td><td>Andorra la Vella</td></tr>
        <tr><td>Bulgaria</td><td>Sofia</td></tr>
      </table>
    </main>
    <footer>Copyright nobody, all rights reserved.</footer>
  </body>
</html>
"""


def listing_page(rows: int) -> bytes:
    """A page whose content lives in repeated labelled blocks, like the country list test page."""
    blocks = "".join(
        f"""
        <div class="country">
          <h3 class="country-name"><i class="flag-icon"></i>Country{i}</h3>
          <div class="country-info">
            <span class="country-capital">Capital{i}</span>
            <span class="country-population">{1000 + i}</span>
          </div>
        </div>"""
        for i in range(rows)
    )
    return f"""<html><head>
        <style>body {{ color: #abcdef; }}</style>
        <script>function trackVisitor() {{ return jQuery.ajax("/beacon"); }}</script>
      </head><body>
        <nav><a href="/">Home</a></nav>
        <h1>Countries</h1><p>A list of countries with their capitals.</p>
        <div class="container">{blocks}</div>
        <footer>Copyright nobody.</footer>
      </body></html>""".encode()


def in_scope(url, target):
    return any(pattern.match(target) for pattern in scope_patterns(url))


def test_extraction_drops_scripts_and_styles():
    text = extract_text(PAGE.encode())
    # the old bs4 `soup.text` extractor returned every string in the document, JavaScript included
    assert "jQuery" not in text
    assert "trackVisitor" not in text
    assert "#abcdef" not in text


def test_extraction_keeps_table_content():
    text = extract_text(PAGE.encode())
    assert "Bulgaria" in text
    assert "Sofia" in text


def test_extraction_keeps_every_row_of_a_listing_page():
    # trafilatura's main content extract() drops the labels out of pages shaped like this while
    # duplicating their data, and does it to *longer* output, so nothing downstream can notice
    text = extract_text(listing_page(20))
    for i in range(20):
        assert f"Country{i}" in text, f"Country{i} was dropped by extraction"
        assert f"Capital{i}" in text


def test_extraction_keeps_a_page_with_nothing_but_boilerplate():
    text = extract_text(b"<html><body><nav><a href='/'>Home</a></nav></body></html>")
    assert "Home" in text


def test_crawl_scope_is_the_url_not_the_host():
    url = "https://www.scrapethissite.com/pages/simple/"
    assert in_scope(url, "https://www.scrapethissite.com/pages/simple/page/2")
    assert in_scope(url, "https://www.scrapethissite.com/pages/simple/?page=2")
    # the page itself, linked without its trailing slash
    assert in_scope(url, "https://www.scrapethissite.com/pages/simple")
    # everything the old max_depth=50 domain wide crawl would have pulled in
    assert not in_scope(url, "https://www.scrapethissite.com/")
    assert not in_scope(url, "https://www.scrapethissite.com/lessons/")
    assert not in_scope(url, "https://www.scrapethissite.com/pages/")
    assert not in_scope(url, "https://www.scrapethissite.com/pages/simple-other/")


def test_crawl_scope_ignores_a_trailing_slash():
    targets = [
        "https://www.scrapethissite.com/pages",
        "https://www.scrapethissite.com/pages/",
        "https://www.scrapethissite.com/pages/simple/",
        "https://www.scrapethissite.com/lessons/",
        "https://www.scrapethissite.com/",
    ]
    without = "https://www.scrapethissite.com/pages"
    for target in targets:
        assert in_scope(without, target) == in_scope(f"{without}/", target), target


def test_crawl_scope_never_widens_to_the_host():
    # a single segment path used to reduce to "https://example.com/", authorising the whole site
    url = "https://example.com/about"
    assert in_scope(url, "https://example.com/about")
    assert in_scope(url, "https://example.com/about/team")
    assert not in_scope(url, "https://example.com/careers")
    assert not in_scope(url, "https://example.com/")


def test_crawl_scope_of_a_bare_domain_is_the_whole_host():
    url = "https://example.com/"
    assert in_scope(url, "https://example.com/")
    assert in_scope(url, "https://example.com/anything/deep")


def test_same_origin_ignores_default_ports():
    assert same_origin("https://example.com/a", "https://example.com:443/b")
    assert not same_origin("https://example.com/a", "http://example.com/a")
    assert not same_origin("https://example.com/a", "https://other.example.com/a")


async def test_public_address_is_allowed():
    # a literal address so this needs no DNS
    await check_url_allowed("https://93.184.216.34/index.html")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9200/",
        "http://[::1]:9200/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://0.0.0.0/",
    ],
)
async def test_internal_addresses_are_rejected(url):
    with pytest.raises(ForbiddenUrlError):
        await check_url_allowed(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9200/",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
async def test_loopback_and_metadata_stay_rejected_for_private_deployments(
    url, monkeypatch
):
    monkeypatch.setenv("SHABTI_CRAWL_ALLOW_PRIVATE_NETWORKS", "True")
    with pytest.raises(ForbiddenUrlError):
        await check_url_allowed(url)


async def test_private_addresses_can_be_opted_into(monkeypatch):
    monkeypatch.setenv("SHABTI_CRAWL_ALLOW_PRIVATE_NETWORKS", "True")
    await check_url_allowed("http://10.0.0.1/wiki")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/pub",
        "https://user:secret@example.com/",
    ],
)
async def test_unsupported_url_shapes_are_rejected(url):
    with pytest.raises(ForbiddenUrlError):
        await check_url_allowed(url)
