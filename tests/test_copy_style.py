"""Copy style and brief formatting tests."""

from advoi.copy_style import format_briefs_spoken, normalize_brief_title, plain_copy


def test_normalize_brief_title_strips_prefix():
    assert normalize_brief_title("Open brief: ADVoi voice launch") == "ADVoi voice launch"


def test_format_briefs_spoken_natural():
    titles = [
        "Open brief: ADVoi voice launch, validate PWA",
        "Open brief: Shelve secrets, push keys",
        "Open brief: Portfolio registration",
    ]
    spoken = format_briefs_spoken(titles)
    assert "Open brief:" not in spoken
    assert "You have 3 open briefs" in spoken
    assert "First, ADVoi voice launch" in spoken
    assert "Pulling open briefs" not in spoken


def test_format_briefs_spoken_single():
    assert format_briefs_spoken(["Staging catch-up"]) == "You have one open brief: Staging catch-up."


def test_plain_copy_strips_em_dash():
    assert plain_copy("Hello\u2014world") == "Hello, world"