"""Synthetic MinerU table boundaries: content preservation and no HTML execution."""
import pytest
from app.services.cn_resume_optimizer_source import normalize_optimizer_source,UnsupportedResumeMarkup


def test_table_cells_rows_contacts_entities_and_line_breaks_keep_all_visible_content():
    original='# Synthetic Candidate\n<table border="1"><thead><tr><th>Role &amp; company</th><th>Dates</th></tr></thead><tbody><tr><td rowspan="2">Backend Engineer<br/>Synthetic Labs</td><td>2023–2025</td></tr><tr><td>28% improvement | 12 services</td></tr></tbody><tfoot><tr><td colspan="2">synthetic@example.invalid<br>+1 202 555 0142</td></tr></tfoot></table>\n## Education\nSynthetic University'
    normalized=normalize_optimizer_source(original)
    assert normalized=='# Synthetic Candidate\nRole & company | Dates\nBackend Engineer\nSynthetic Labs | 2023–2025\n28% improvement | 12 services\nsynthetic@example.invalid\n+1 202 555 0142\n\n\n## Education\nSynthetic University'
    for content in ('Backend Engineer','Synthetic Labs','2023–2025','28% improvement','12 services','synthetic@example.invalid','+1 202 555 0142','Synthetic University'):
        assert normalized.count(content)==1
    assert '<' not in normalized and 'rowspan' not in normalized


def test_plain_markdown_without_markup_is_unchanged():
    original='# Synthetic Candidate\n\nPython & SQL | 2024\nScore < 3 and C++ > 0.'
    assert normalize_optimizer_source(original)==original


@pytest.mark.parametrize('markup',[
    '<script>fetch("https://example.invalid/private")</script>',
    '<style>body{background:url(https://example.invalid/x)}</style>',
    '<img src="https://example.invalid/private">',
    '<a href="https://example.invalid">Portfolio fact</a>',
    '<svg><text>Candidate fact</text></svg>',
    '<div>Candidate fact</div>',
    '<table><caption>Candidate fact</caption></table>',
    '<table onclick="alert(1)"><tr><td>Fact</td></tr></table>',
    '<table style="display:none"><tr><td>Fact</td></tr></table>',
    '<table><tr><td>Unclosed fact',
    '<table><tr>Fact outside cell<td>Other fact</td></tr></table>',
    '<table><tr><td>Fact</tr></td></table>',
    '<table><tr><td><table><tr><td>Nested fact</td></tr></table></td></tr></table>',
    '<!-- Hidden candidate fact -->',
    '<!DOCTYPE html>',
    '<?process candidate fact?>',
    '&lt;script&gt;Untrusted literal marker&lt;/script&gt;',
])
def test_unknown_or_ambiguous_markup_is_rejected_without_dropping_facts(markup):
    with pytest.raises(UnsupportedResumeMarkup):
        normalize_optimizer_source('# Candidate\n'+markup)
