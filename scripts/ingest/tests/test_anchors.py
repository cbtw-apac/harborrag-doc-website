from ingest.anchors import heading_text, page_anchors, slugify


def test_slugify_matches_github_slugger():
    assert slugify("Policy and audit status") == "policy-and-audit-status"
    assert slugify("What's new in 2.0?") == "whats-new-in-20"
    assert slugify("harbor_rag_core / API") == "harbor_rag_core--api"
    assert slugify("Café déjà vu") == "café-déjà-vu"


def test_heading_text_strips_inline_markdown():
    assert heading_text("Use `harborrag` with [MCP](x.md) **now**") == "Use harborrag with MCP now"
    assert heading_text("<a id='x'></a>Install") == "Install"


def test_page_anchors_headings_duplicates_and_title():
    body = (
        "# Title\n\n"
        "## Usage\n\n"
        "```bash\n# not a heading\n```\n\n"
        "### Usage\n\n"
        "## Usage ##\n\n"
        "## Custom {#my-id}\n\n"
        '<a id="manual"></a>\n'
        "# Second H1\n"
    )

    assert page_anchors(body) == {
        "usage",
        "usage-1",
        "usage-2",
        "my-id",
        "manual",
        "second-h1",
    }