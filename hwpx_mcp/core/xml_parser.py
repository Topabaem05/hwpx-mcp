"""
Secure XML Parser for HWPX (OWPML) processing.
Uses defusedxml to prevent XML attacks (XXE, Billion Laughs).
"""

from typing import Union, Dict
from lxml import etree
import defusedxml.lxml as safe_lxml


class SecureXmlParser:
    """
    Secure XML parser wrapper using defusedxml.
    Provides standard OWPML namespace mappings.
    """

    # OWPML Namespace Map
    NS_MAP: Dict[str, str] = {
        "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
        "hs": "http://www.hancom.co.kr/hwpml/2011/section",
        "hc": "http://www.hancom.co.kr/hwpml/2011/core",
        "hm": "http://www.hancom.co.kr/hwpml/2011/metadata",
        "hpf": "http://www.hancom.co.kr/hwpml/2011/package/font",
        "hh": "http://www.hancom.co.kr/hwpml/2011/head",
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    @staticmethod
    def parse_string(xml_content: Union[str, bytes]) -> etree._Element:
        """
        Safely parse XML string.

        Args:
            xml_content: XML content as string or bytes

        Returns:
            lxml Element object (root)
        """
        # defusedxml automatically disables DTDs and entities
        return safe_lxml.fromstring(xml_content)

    @staticmethod
    def parse_file(file_path: str) -> etree._Element:
        """
        Safely parse XML file.

        Args:
            file_path: Path to XML file

        Returns:
            lxml Element object (root)
        """
        # safe_lxml.parse returns an ElementTree, we usually want the root Element
        tree = safe_lxml.parse(file_path)
        return tree.getroot()

    @staticmethod
    def to_string(element: etree._Element, pretty_print: bool = False) -> str:
        """
        Convert Element back to string.
        """
        return etree.tostring(element, encoding="unicode", pretty_print=pretty_print)
