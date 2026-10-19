"""A narrow MinerU-table-to-text boundary, never an HTML renderer.

Only known inert table layout is accepted. Unknown markup is rejected before
quota/provider admission rather than silently dropping candidate information.
"""
from html.parser import HTMLParser
import re


class UnsupportedResumeMarkup(ValueError):
    def __init__(self):
        super().__init__("unsupported_source_markup")


class _MineruTableText(HTMLParser):
    tags={"table","tr","td","th","thead","tbody","tfoot","br"}
    layout_attributes={"border","cellpadding","cellspacing","width","height","align","valign","rowspan","colspan"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.parts=[]
        self.cells=None
        self.cell=None

    def newline(self):
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self,tag,attrs):
        if tag not in self.tags or any(name not in self.layout_attributes for name,_ in attrs):
            raise UnsupportedResumeMarkup()
        if any(value is not None and (len(value)>100 or re.search(r"[<>]",value)) for _,value in attrs):
            raise UnsupportedResumeMarkup()
        if tag=="br":
            if self.cell is not None:
                self.cell.append("\n")
            elif self.stack:
                raise UnsupportedResumeMarkup()
            else:
                self.parts.append("\n")
            return
        parent=self.stack[-1] if self.stack else None
        allowed={"table":{None},"thead":{"table"},"tbody":{"table"},"tfoot":{"table"},
                 "tr":{"table","thead","tbody","tfoot"},"td":{"tr"},"th":{"tr"}}
        if parent not in allowed[tag]:
            raise UnsupportedResumeMarkup()
        self.stack.append(tag)
        if tag=="table":
            self.newline()
        elif tag=="tr":
            self.cells=[]
        elif tag in ("td","th"):
            self.cell=[]

    def handle_endtag(self,tag):
        if tag=="br" or not self.stack or self.stack[-1]!=tag:
            raise UnsupportedResumeMarkup()
        self.stack.pop()
        if tag in ("td","th"):
            self.cells.append("".join(self.cell).strip())
            self.cell=None
        elif tag=="tr":
            self.parts.append(" | ".join(self.cells)+"\n")
            self.cells=None
        elif tag=="table":
            self.parts.append("\n")

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag!="br":
            self.handle_endtag(tag)

    def handle_data(self,data):
        if self.cell is not None:
            self.cell.append(data)
        elif self.stack:
            # Formatting whitespace may be discarded; any text outside a cell
            # is ambiguous and is rejected instead of silently losing a fact.
            if data.strip():
                raise UnsupportedResumeMarkup()
        else:
            self.parts.append(data)

    def handle_comment(self,_data):
        raise UnsupportedResumeMarkup()

    def handle_decl(self,_decl):
        raise UnsupportedResumeMarkup()

    def handle_pi(self,_data):
        raise UnsupportedResumeMarkup()

    def unknown_decl(self,_data):
        raise UnsupportedResumeMarkup()


def normalize_optimizer_source(text: str) -> str:
    parser=_MineruTableText()
    try:
        parser.feed(text)
        parser.close()
        if parser.stack or parser.cell is not None or parser.cells is not None:
            raise UnsupportedResumeMarkup()
        result="".join(parser.parts).strip()
        # Escaped markup is still literal untrusted text, never reparsed as HTML.
        # Reject it early if it cannot form an allowed plain-text resume draft.
        if re.search(r"</?[A-Za-z][^>]*>",result):
            raise UnsupportedResumeMarkup()
        return result
    except UnsupportedResumeMarkup:
        raise
    except (ValueError,AssertionError):
        raise UnsupportedResumeMarkup() from None
