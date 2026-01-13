"""
Equation Tools for HWP MCP Server
LaTeX equation to Base64 image conversion tools
"""

import logging
import base64
from typing import Optional, Dict, Any, Callable
from io import BytesIO

from pydantic import BaseModel, Field

logger = logging.getLogger("hwp-mcp-extended.equations")


class CreateEquationInput(BaseModel):
    """Equation creation input schema"""

    equation: str = Field(
        ...,
        description="Equation (LaTeX format)",
        examples=[
            "E = mc^2",
            "\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}",
            "\\int_0^\\infty e^{-x^2} dx",
        ],
    )
    input_format: str = Field(default="latex", description="Input format")
    font_size: int = Field(default=24, ge=8, le=72, description="Font size")
    color: str = Field(default="black", description="Font color")
    return_base64: bool = Field(default=True, description="Return Base64 image")


class CreateEquationOutput(BaseModel):
    """Equation creation output schema"""

    status: str = Field(..., description="Status")
    equation: str = Field(..., description="Input equation")
    image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded image"
    )
    mime_type: Optional[str] = Field(default=None, description="MIME type")


EQUATION_COMMANDS = {
    "fractions": {
        "latex": "\\frac{a}{b}",
        "text": "a over b",
        "description": "Fraction",
    },
    "sqrt": {"latex": "\\sqrt{x}", "text": "sqrt x", "description": "Square root"},
    "power": {"latex": "x^{n}", "text": "x^n", "description": "Power"},
    "subscript": {"latex": "x_{n}", "text": "x_n", "description": "Subscript"},
    "alpha": {"latex": "\\alpha", "text": "alpha", "description": "Alpha"},
    "beta": {"latex": "\\beta", "text": "beta", "description": "Beta"},
    "gamma": {"latex": "\\gamma", "text": "gamma", "description": "Gamma"},
    "delta": {"latex": "\\delta", "text": "delta", "description": "Delta"},
    "pi": {"latex": "\\pi", "text": "pi", "description": "Pi"},
    "sigma": {"latex": "\\sigma", "text": "sigma", "description": "Sigma"},
    "theta": {"latex": "\\theta", "text": "theta", "description": "Theta"},
    "omega": {"latex": "\\omega", "text": "omega", "description": "Omega"},
    "integral": {"latex": "\\int", "text": "int", "description": "Integral"},
    "sum": {"latex": "\\sum", "text": "sum", "description": "Sum"},
    "product": {"latex": "\\prod", "text": "prod", "description": "Product"},
    "limit": {"latex": "\\lim", "text": "lim", "description": "Limit"},
    "leq": {"latex": "\\leq", "text": "<=", "description": "Less or equal"},
    "geq": {"latex": "\\geq", "text": ">=", "description": "Greater or equal"},
    "neq": {"latex": "\\neq", "text": "!=", "description": "Not equal"},
    "approx": {"latex": "\\approx", "text": "~=", "description": "Approximately"},
    "in": {"latex": "\\in", "text": "in", "description": "Element of"},
    "subset": {"latex": "\\subset", "text": "subset", "description": "Subset"},
    "union": {"latex": "\\cup", "text": "union", "description": "Union"},
    "intersection": {"latex": "\\cap", "text": "inter", "description": "Intersection"},
    "matrix": {
        "latex": "\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}",
        "text": "pmatrix{a&b#c&d}",
        "description": "Matrix",
    },
    "arrow": {"latex": "\\rightarrow", "text": "->", "description": "Arrow"},
    "mapsto": {"latex": "\\mapsto", "text": "mapsto", "description": "Map to"},
}


def _create_equation_base64(
    equation: str,
    input_format: str = "latex",
    font_size: int = 24,
    color: str = "black",
) -> Optional[str]:
    """Create LaTeX equation image and encode as Base64 using matplotlib mathtext."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.mathtext import MathTextParser

        # Prepare the equation for matplotlib
        latex_formula = equation
        if input_format == "latex":
            # Ensure proper LaTeX formatting for mathtext
            # mathtext uses $...$ delimiters
            if not latex_formula.startswith("$"):
                latex_formula = f"${latex_formula}$"

        # Create figure with appropriate size
        fig_width = len(equation) * font_size / 12 + 1
        fig_height = font_size / 8 + 0.5
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=100)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        # Render the equation using mathtext
        ax.text(
            0.5,
            0.5,
            latex_formula,
            fontsize=font_size,
            color=color,
            ha="center",
            va="center",
            transform=ax.transAxes,
            usetex=False,  # Use mathtext instead of full LaTeX
        )

        # Remove axes
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(
            buffer,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
            transparent=True,
        )
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)

        return image_base64

    except Exception as e:
        logger.error(f"Failed to create equation image: {e}")
        return None


def _parse_latex_to_matplotlib(latex: str, input_format: str) -> str:
    """Convert LaTeX to matplotlib-compatible format."""
    if input_format == "latex":
        # Basic LaTeX to mathtext conversions
        # mathtext supports most common LaTeX math commands
        return latex
    else:
        return latex


def register_equation_tools(mcp, get_pyhwp_adapter: Callable) -> None:
    """Register equation tools with MCP server."""

    @mcp.tool()
    def hwp_create_equation(
        equation: str,
        input_format: str = "latex",
        font_size: int = 24,
        color: str = "black",
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create equation and return as Base64 image.

        Args:
            equation: Equation (LaTeX or text format)
            input_format: Input format (latex, text)
            font_size: Font size (8-72)
            color: Font color
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
                - status: Operation status (success, error)
                - equation: Input equation
                - image_base64: Base64 encoded image
        """
        try:
            if not equation or not equation.strip():
                return {"status": "error", "error": "Equation is required"}

            valid_formats = ["latex", "text"]
            if input_format not in valid_formats:
                return {
                    "status": "error",
                    "error": f"Invalid format: {input_format}. Valid: {valid_formats}",
                }

            equation_base64 = _create_equation_base64(
                equation=equation,
                input_format=input_format,
                font_size=font_size,
                color=color,
            )

            if not equation_base64:
                return {
                    "status": "error",
                    "error": "Failed to create equation image. Check equation syntax.",
                }

            result = {
                "status": "success",
                "equation": equation,
                "image_base64": equation_base64 if return_base64 else None,
                "mime_type": "image/png",
            }

            return result

        except Exception as e:
            logger.error(f"Error creating equation: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_insert_fraction(
        numerator: str, denominator: str, return_base64: bool = True
    ) -> Dict[str, Any]:
        """
        Create fraction.

        Args:
            numerator: Numerator
            denominator: Denominator
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        equation = f"\\frac{{{numerator}}}{{{denominator}}}"
        return hwp_create_equation(
            equation=equation, input_format="latex", return_base64=return_base64
        )

    @mcp.tool()
    def hwp_insert_integral(
        integrand: str,
        variable: str = "x",
        lower_limit: Optional[str] = None,
        upper_limit: Optional[str] = None,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create integral.

        Args:
            integrand: Integrand
            variable: Integration variable
            lower_limit: Lower limit (optional)
            upper_limit: Upper limit (optional)
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        if lower_limit and upper_limit:
            equation = (
                f"\\int_{{{lower_limit}}}^{{{upper_limit}}} {integrand} d{variable}"
            )
        else:
            equation = f"\\int {integrand} d{variable}"

        return hwp_create_equation(
            equation=equation, input_format="latex", return_base64=return_base64
        )

    @mcp.tool()
    def hwp_insert_sum(
        expression: str,
        index_var: str = "n",
        lower: str = "0",
        upper: str = "\\infty",
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create summation (Sigma).

        Args:
            expression: Summation expression
            index_var: Index variable
            lower: Start value
            upper: End value
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        equation = f"\\sum_{{{index_var}={lower}}}^{{{upper}}} {expression}"
        return hwp_create_equation(
            equation=equation, input_format="latex", return_base64=return_base64
        )

    @mcp.tool()
    def hwp_insert_limit(
        expression: str,
        variable: str = "x",
        approach: str = "0",
        direction: Optional[str] = None,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create limit.

        Args:
            expression: Limit expression
            variable: Limit variable
            approach: Approach value
            direction: Direction (+, -, or None)
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        if direction == "+":
            equation = f"\\lim_{{{variable} \\to {approach}^+}} {expression}"
        elif direction == "-":
            equation = f"\\lim_{{{variable} \\to {approach}^-}} {expression}"
        else:
            equation = f"\\lim_{{{variable} \\to {approach}}} {expression}"

        return hwp_create_equation(
            equation=equation, input_format="latex", return_base64=return_base64
        )

    @mcp.tool()
    def hwp_insert_matrix(
        rows: list[list[str]],
        matrix_type: str = "parentheses",
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create matrix.

        Args:
            rows: Matrix data (e.g., [["a", "b"], ["c", "d"]])
            matrix_type: Matrix type (parentheses, brackets, vertical)
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        if matrix_type == "parentheses":
            latex = (
                "\\begin{pmatrix} "
                + " \\\\ ".join(" & ".join(row) for row in rows)
                + " \\end{pmatrix}"
            )
        elif matrix_type == "brackets":
            latex = (
                "\\begin{bmatrix} "
                + " \\\\ ".join(" & ".join(row) for row in rows)
                + " \\end{bmatrix}"
            )
        elif matrix_type == "vertical":
            latex = (
                "\\begin{vmatrix} "
                + " \\\\ ".join(" & ".join(row) for row in rows)
                + " \\end{vmatrix}"
            )
        else:
            return {"status": "error", "error": f"Unknown matrix type: {matrix_type}"}

        return hwp_create_equation(
            equation=latex, input_format="latex", return_base64=return_base64
        )

    @mcp.tool()
    def hwp_get_equation_commands() -> Dict[str, Any]:
        """
        Get list of available equation commands.

        Returns:
            dict: Equation command list
        """
        commands_by_category = {
            "basic": {
                "fractions": EQUATION_COMMANDS["fractions"],
                "sqrt": EQUATION_COMMANDS["sqrt"],
                "power": EQUATION_COMMANDS["power"],
                "subscript": EQUATION_COMMANDS["subscript"],
            },
            "greek": {
                k: v
                for k, v in EQUATION_COMMANDS.items()
                if k
                in ["alpha", "beta", "gamma", "delta", "pi", "sigma", "theta", "omega"]
            },
            "operators": {
                "integral": EQUATION_COMMANDS["integral"],
                "sum": EQUATION_COMMANDS["sum"],
                "product": EQUATION_COMMANDS["product"],
                "limit": EQUATION_COMMANDS["limit"],
            },
            "relations": {
                "leq": EQUATION_COMMANDS["leq"],
                "geq": EQUATION_COMMANDS["geq"],
                "neq": EQUATION_COMMANDS["neq"],
                "approx": EQUATION_COMMANDS["approx"],
            },
            "sets": {
                "in": EQUATION_COMMANDS["in"],
                "subset": EQUATION_COMMANDS["subset"],
                "union": EQUATION_COMMANDS["union"],
                "intersection": EQUATION_COMMANDS["intersection"],
            },
            "matrices": {"matrix": EQUATION_COMMANDS["matrix"]},
        }

        return {
            "categories": list(commands_by_category.keys()),
            "commands": commands_by_category,
            "output_formats": ["base64"],
        }
