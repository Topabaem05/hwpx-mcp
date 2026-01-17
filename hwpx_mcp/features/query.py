"""
High-performance XPath query engine for HWPX documents.
Leverages lxml's C-based XPath 1.0 engine.
"""

from typing import List, Union
from lxml import etree
from ..core.xml_parser import SecureXmlParser


class HwpxQueryEngine:
    """
    XPath query engine with built-in OWPML namespace support.
    """

    @staticmethod
    def execute_xpath(
        element: etree._Element, xpath_query: str
    ) -> List[Union[etree._Element, str, int, float]]:
        """
        Execute raw XPath query on an element.

        Args:
            element: Root element to search from
            xpath_query: XPath string (use hp:, hs: prefixes)

        Returns:
            List of matches (elements, strings, etc.)
        """
        return element.xpath(xpath_query, namespaces=SecureXmlParser.NS_MAP)

    @staticmethod
    def find_large_tables(
        element: etree._Element, min_rows: int = 5
    ) -> List[etree._Element]:
        """
        Find tables with at least min_rows.

        Args:
            element: Root element
            min_rows: Minimum row count
        """
        # hp:table has 'rowCnt' attribute
        xpath = f".//hp:table[@rowCnt >= {min_rows}]"
        return element.xpath(xpath, namespaces=SecureXmlParser.NS_MAP)

    @staticmethod
    def find_images_by_size(
        element: etree._Element, min_width_mm: float = 0, min_height_mm: float = 0
    ) -> List[etree._Element]:
        """
        Find images larger than specified dimensions.
        Note: HWPX stores dimensions in HwpUnit (1mm ~ 283.465 HU)
        """
        # 1mm = 283.465 HwpUnit
        w_hu = int(min_width_mm * 283.465)
        h_hu = int(min_height_mm * 283.465)

        # hp:pic -> hp:shapeObject -> hp:sz (width, height)
        # Structure is <hp:pic ...> <hp:sz width="..." height="..." /> </hp:pic>
        # Need to check hp:sz child of hp:pic/hp:shapeObject ??
        # Actually hp:pic is inside hp:run. Picture properties are in hp:pic itself or children.
        # Simple query for hp:pic first.
        # <hp:pic> usually has <hc:sz width=".." height="..">

        xpath = f".//hp:pic/hc:sz[@width >= {w_hu} and @height >= {h_hu}]/.."
        return element.xpath(xpath, namespaces=SecureXmlParser.NS_MAP)

    @staticmethod
    def find_text_containing(
        element: etree._Element, keyword: str
    ) -> List[etree._Element]:
        """
        Find text runs (<hp:t>) containing specific keyword.
        """
        # XPath 1.0 contains() function
        # Keyword needs escaping for XPath string
        safe_keyword = keyword.replace("'", "")  # Basic sanitization
        xpath = f".//hp:t[contains(text(), '{safe_keyword}')]"
        return element.xpath(xpath, namespaces=SecureXmlParser.NS_MAP)
