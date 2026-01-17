"""
Pydantic-XML models for OWPML (HWPX) structure.
Allows object-oriented manipulation of HWPX documents.
"""

from typing import List, Optional
from pydantic_xml import BaseXmlModel, attr, element

# OWPML Namespaces
NS_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS_HS = "http://www.hancom.co.kr/hwpml/2011/section"
NS_HC = "http://www.hancom.co.kr/hwpml/2011/core"


class HwpxText(BaseXmlModel, tag="t", ns="hp", nsmap={"hp": NS_HP}):
    """Text content element (<hp:t>)"""

    content: str


class HwpxRun(BaseXmlModel, tag="run", ns="hp", nsmap={"hp": NS_HP}):
    """Run element (<hp:run>) - smallest formatting unit"""

    # attributes like charPrID (style) can be added here
    char_pr_id: Optional[int] = attr(name="charPrID", default=None)
    text: Optional[HwpxText] = element(tag="t", default=None)


class HwpxParagraph(BaseXmlModel, tag="p", ns="hp", nsmap={"hp": NS_HP}):
    """Paragraph element (<hp:p>)"""

    id: int = attr()
    para_pr_id: Optional[int] = attr(name="paraPrID", default=None)
    style_id: Optional[int] = attr(name="styleID", default=None)
    page_break: bool = attr(name="pageBreak", default=False)
    column_break: bool = attr(name="columnBreak", default=False)

    runs: List[HwpxRun] = element(tag="run", default=[])

    def get_text(self) -> str:
        """Extract plain text from paragraph"""
        return "".join(
            run.text.content for run in self.runs if run.text and run.text.content
        )


class HwpxSection(BaseXmlModel, tag="sec", ns="hs", nsmap={"hs": NS_HS, "hp": NS_HP}):
    """Section element (<hs:sec>)"""

    paragraphs: List[HwpxParagraph] = element(tag="p")

    def get_text(self) -> str:
        """Extract plain text from section"""
        return "\n".join(p.get_text() for p in self.paragraphs)
