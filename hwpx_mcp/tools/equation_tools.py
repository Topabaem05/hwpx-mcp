"""
Equation tools for HWP MCP Server.
"""
import logging
import re
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from hwpx_mcp.tools.windows_hwp_controller import get_hwp_controller

logger = logging.getLogger("hwp-mcp-extended.equations")

def convert_latex_to_hwp(latex: str) -> str:
    """Convert basic LaTeX syntax to HWP Equation Script."""
    script = latex
    
    # \frac{a}{b} -> {a} over {b}
    # Nested fracs might fail with regex, but basic support is helpful
    script = re.sub(r"\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}", r"{\1} over {\2}", script)
    
    # Common symbols
    replacements = [
        (r"\sqrt", "sqrt"),
        (r"\int", "int"),
        (r"\sum", "sum"),
        (r"\prod", "prod"),
        (r"\lim", "lim"),
        (r"\infty", "inf"),
        (r"\times", "times"),
        (r"\cdot", "cdot"),
        (r"\pm", "+-"),
        (r"\div", "div"),
        (r"\neq", "!="),
        (r"\leq", "<="),
        (r"\geq", ">="),
        (r"\approx", "approx"),
        
        # Greek letters
        (r"\alpha", "alpha"), (r"\beta", "beta"), (r"\gamma", "gamma"),
        (r"\delta", "delta"), (r"\epsilon", "epsilon"), (r"\zeta", "zeta"),
        (r"\eta", "eta"), (r"\theta", "theta"), (r"\iota", "iota"),
        (r"\kappa", "kappa"), (r"\lambda", "lambda"), (r"\mu", "mu"),
        (r"\nu", "nu"), (r"\xi", "xi"), (r"\pi", "pi"),
        (r"\rho", "rho"), (r"\sigma", "sigma"), (r"\tau", "tau"),
        (r"\phi", "phi"), (r"\chi", "chi"), (r"\psi", "psi"),
        (r"\omega", "omega"),
        
        # Uppercase Greek
        (r"\Delta", "DELTA"), (r"\Gamma", "GAMMA"), (r"\Lambda", "LAMBDA"),
        (r"\Omega", "OMEGA"), (r"\Phi", "PHI"), (r"\Pi", "PI"),
        (r"\Psi", "PSI"), (r"\Sigma", "SIGMA"), (r"\Theta", "THETA")
    ]
    
    for tex, hwp in replacements:
        script = script.replace(tex, hwp)
        
    # Subscripts/Superscripts usually work as is (^, _)
    
    return script

def register_equation_tools(mcp: FastMCP, get_pyhwp_adapter=None) -> None:
    """Register equation tools with MCP server."""

    @mcp.tool()
    def hwp_create_equation(equation: str) -> Dict[str, Any]:
        """
        Insert an equation into the HWP document.
        Uses HWP Equation Script syntax (automatically converts basic LaTeX).
        
        Args:
            equation: Equation script (LaTeX or HWP format)
        """
        controller = get_hwp_controller()
        if not controller:
            return {"success": False, "error": "Windows HWP controller required"}
            
        if not controller.is_hwp_running:
            if not controller.connect():
                return {"success": False, "error": "Failed to connect to HWP"}

        # Try to convert if it looks like LaTeX
        hwp_script = equation
        if "\\" in equation:
            hwp_script = convert_latex_to_hwp(equation)
            
        success = controller.create_equation(hwp_script)
        
        return {
            "success": success,
            "message": "Equation inserted" if success else "Failed to insert equation",
            "original": equation,
            "converted_script": hwp_script
        }
