"""
Smart XML Editor for HWPX.
Uses xmldiff to validate and filter AI-generated edits.
"""

from xmldiff import main as xml_diff
from ..core.xml_parser import SecureXmlParser

class HwpxSmartEditor:
    """
    Validates XML modifications to prevent structural damage.
    """
    
    # Critical tags that should not be deleted or renamed
    CRITICAL_TAGS = [
        "sec", "p", "run", "table", "colDef", "row", "col"
    ]

    @classmethod
    def validate_edits(cls, original_xml: str, modified_xml: str) -> dict:
        """
        Compare original and modified XML.
        Returns:
            dict: { "safe": bool, "diffs": list, "message": str }
        """
        try:
            # 1. Parse validation (Security check)
            SecureXmlParser.parse_string(original_xml)
            SecureXmlParser.parse_string(modified_xml)

            # 2. Calculate diff
            # xmldiff.main.diff_texts returns a list of action objects
            diffs = xml_diff.diff_texts(original_xml, modified_xml)
            
            unsafe_actions = []
            diff_summary = []

            for action in diffs:
                action_str = str(action)
                diff_summary.append(action_str)
                
                # Check for DeleteNode or RenameNode on critical structure
                # Action format example: "DeleteNode /hp:sec[1]/hp:p[2]"
                if "DeleteNode" in action_str or "RenameNode" in action_str:
                    for tag in cls.CRITICAL_TAGS:
                        # Check if tag appears in the path or node name
                        # Basic heuristic: if "hp:{tag}" or "hs:{tag}" is in the action string
                        if f":{tag}" in action_str:
                            unsafe_actions.append(action_str)
                            break
            
            if unsafe_actions:
                return {
                    "safe": False,
                    "message": "Unsafe structural changes detected. Modifications rejected.",
                    "unsafe_actions": unsafe_actions
                }
            
            return {
                "safe": True,
                "message": "Edits are structure-safe.",
                "diffs": diff_summary
            }

        except Exception as e:
            return {"safe": False, "message": f"Error during smart edit validation: {str(e)}"}
