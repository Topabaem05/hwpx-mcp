"""
XML Validator for HWPX content.
Supports both XSD schema validation and Pydantic model validation.
"""

from typing import Optional, Union, Any, Type
import xmlschema
from lxml import etree
from pydantic_xml import BaseXmlModel
from .xml_parser import SecureXmlParser


class XmlValidator:
    """
    Validator engine for HWPX XML content.
    """

    def __init__(self, xsd_path: Optional[str] = None):
        """
        Initialize validator.

        Args:
            xsd_path: Path to OWPML XSD file (optional)
        """
        self.schema: Optional[xmlschema.XMLSchema] = None
        if xsd_path:
            try:
                self.schema = xmlschema.XMLSchema(xsd_path)
            except Exception as e:
                # Log error but don't fail initialization
                print(f"Warning: Failed to load XSD from {xsd_path}: {e}")

    def validate_syntax(self, xml_content: Union[str, bytes]) -> bool:
        """
        Validate XML syntax and security (well-formedness).
        """
        try:
            SecureXmlParser.parse_string(xml_content)
            return True
        except Exception:
            return False

    def validate_schema(self, xml_content: Union[str, bytes]) -> bool:
        """
        Validate against loaded XSD schema.
        Returns True if no schema is loaded (pass-through).
        """
        if not self.schema:
            return True

        try:
            # xmlschema works with string/file, not lxml objects directly usually
            # Convert bytes to string if needed
            content = (
                xml_content
                if isinstance(xml_content, str)
                else xml_content.decode("utf-8")
            )
            return self.schema.is_valid(content)
        except Exception:
            return False

    @staticmethod
    def validate_model(
        model_class: Type[BaseXmlModel], xml_content: Union[str, bytes]
    ) -> bool:
        """
        Validate if XML matches a Pydantic-XML model structure.
        """
        try:
            model_class.from_xml(xml_content)
            return True
        except Exception:
            return False
