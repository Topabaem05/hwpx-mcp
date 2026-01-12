"""
Chart Tools for HWP MCP Server
matplotlib based chart creation and Base64 encoding tools
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List
import base64
from io import BytesIO

from pydantic import BaseModel, Field

logger = logging.getLogger("hwp-mcp-extended.charts")


class ChartDataset(BaseModel):
    label: str = Field(..., description="Dataset name")
    data: list[float] = Field(..., description="Data values")


class ChartData(BaseModel):
    labels: list[str] = Field(..., description="X-axis label list")
    datasets: list[ChartDataset] = Field(..., description="Dataset list")


VALID_CHART_TYPES = ["bar", "line", "pie", "area", "scatter", "histogram"]


class CreateChartInput(BaseModel):
    chart_type: str = Field(
        ..., description="Chart type (bar, line, pie, area, scatter, histogram)"
    )
    data: ChartData = Field(..., description="Chart data with labels and datasets")
    title: str = Field(default="", description="Chart title")
    xlabel: str = Field(default="", description="X-axis label")
    ylabel: str = Field(default="", description="Y-axis label")
    width: int = Field(default=800, description="Image width in pixels")
    height: int = Field(default=600, description="Image height in pixels")
    color_scheme: str = Field(default="default", description="Color scheme")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_chart_type

    @classmethod
    def validate_chart_type(cls, v):
        if isinstance(v, cls):
            if v.chart_type not in VALID_CHART_TYPES:
                raise ValueError(
                    f"Invalid chart type: {v.chart_type}. Valid: {VALID_CHART_TYPES}"
                )
        return v

    def __init__(self, **data):
        super().__init__(**data)
        if self.chart_type not in VALID_CHART_TYPES:
            raise ValueError(
                f"Invalid chart type: {self.chart_type}. Valid: {VALID_CHART_TYPES}"
            )


def _create_chart_base64(
    chart_type: str,
    data: Dict[str, Any],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    width: int = 800,
    height: int = 600,
    color_scheme: str = "default",
) -> Optional[str]:
    """Create chart with matplotlib and encode as Base64."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib

        matplotlib.use("Agg")

        colors = _get_color_scheme(color_scheme)
        labels = data.get("labels", [])
        datasets = data.get("datasets", [])

        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        _draw_chart_by_type(ax, chart_type, labels, datasets, colors)
        _configure_chart_labels(ax, title, xlabel, ylabel, datasets, chart_type)
        ax.grid(True, linestyle="--", alpha=0.7)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)

        return image_base64

    except Exception as e:
        logger.error(f"Failed to create chart: {e}")
        return None


def _get_color_scheme(color_scheme: str) -> List[str]:
    """Get color scheme for chart."""
    color_schemes = {
        "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        "pastel": ["#ffb3ba", "#ffdfba", "#ffffba", "#baffc9", "#bae1ff"],
        "dark": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7"],
        "monochrome": ["#2c3e50", "#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7"],
    }
    return color_schemes.get(color_scheme, color_schemes["default"])


def _draw_chart_by_type(
    ax, chart_type: str, labels: List[str], datasets: List[Dict], colors: List[str]
) -> None:
    """Draw chart based on type."""
    if chart_type == "bar":
        for i, dataset in enumerate(datasets):
            ax.bar(
                labels,
                dataset["data"],
                label=dataset.get("label", f"Series {i + 1}"),
                color=colors[i % len(colors)],
            )
    elif chart_type == "line":
        for i, dataset in enumerate(datasets):
            ax.plot(
                labels,
                dataset["data"],
                marker="o",
                label=dataset.get("label", f"Series {i + 1}"),
                color=colors[i % len(colors)],
                linewidth=2,
            )
    elif chart_type == "pie":
        if datasets:
            values = datasets[0].get("data", [])
            ax.pie(
                values, labels=labels, autopct="%1.1f%%", colors=colors[: len(values)]
            )
    elif chart_type == "area":
        for i, dataset in enumerate(datasets):
            ax.fill_between(
                labels,
                dataset["data"],
                alpha=0.3,
                label=dataset.get("label", f"Series {i + 1}"),
                color=colors[i % len(colors)],
            )
    elif chart_type == "scatter":
        if datasets:
            ax.scatter(labels, datasets[0].get("data", []), c=colors[0], s=100)
    elif chart_type == "histogram":
        if datasets:
            ax.hist(
                datasets[0].get("data", []), bins=10, color=colors[0], edgecolor="black"
            )


def _configure_chart_labels(
    ax, title: str, xlabel: str, ylabel: str, datasets: List[Dict], chart_type: str
) -> None:
    """Configure chart labels."""
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if len(datasets) > 1 or (chart_type == "bar" and len(datasets) == 1):
        ax.legend()


def register_chart_tools(mcp, get_pyhwp_adapter: Callable) -> None:
    """Register chart tools with MCP server."""

    @mcp.tool()
    def hwp_create_chart(
        chart_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        color_scheme: str = "default",
        width: int = 800,
        height: int = 600,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create chart and return as Base64 image.

        Args:
            chart_type: Chart type (bar, line, pie, area, scatter, histogram)
            data: Chart data with labels and datasets
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            color_scheme: Color theme (default, pastel, dark, monochrome)
            width: Image width in pixels
            height: Image height in pixels
            return_base64: Return Base64 encoded image

        Returns:
            dict: Creation result
                - status: Operation status (success, error)
                - chart_type: Chart type
                - title: Chart title
                - image_base64: Base64 encoded image
                - data_summary: Data summary

        Example:
            hwp_create_chart(
                chart_type="bar",
                data={"labels": ["Jan", "Feb", "Mar"], "datasets": [{"label": "Sales", "data": [100, 150, 200]}]},
                title="Monthly Sales"
            )
        """
        try:
            valid_types = ["bar", "line", "pie", "area", "scatter", "histogram"]
            if chart_type not in valid_types:
                return {
                    "status": "error",
                    "error": f"Invalid chart type: {chart_type}. Valid types: {valid_types}",
                }

            if "labels" not in data or "datasets" not in data:
                return {
                    "status": "error",
                    "error": "Data must contain 'labels' and 'datasets'",
                }

            chart_base64 = _create_chart_base64(
                chart_type=chart_type,
                data=data,
                title=title or "",
                xlabel=xlabel or "",
                ylabel=ylabel or "",
                width=width,
                height=height,
                color_scheme=color_scheme,
            )

            if not chart_base64:
                return {"status": "error", "error": "Failed to create chart image"}

            data_summary = {
                "labels_count": len(data["labels"]),
                "datasets_count": len(data["datasets"]),
                "total_data_points": sum(
                    len(ds.get("data", [])) for ds in data["datasets"]
                ),
            }

            result = {
                "status": "success",
                "chart_type": chart_type,
                "title": title,
                "data_summary": data_summary,
            }

            if return_base64:
                result["image_base64"] = chart_base64
                result["mime_type"] = "image/png"

            return result

        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def hwp_create_bar_chart(
        labels: list[str],
        values: list[float],
        title: Optional[str] = None,
        bar_label: Optional[str] = None,
        color: str = "#1f77b4",
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create simple bar chart.

        Args:
            labels: Bar label list
            values: Bar value list
            title: Chart title
            bar_label: Dataset name
            color: Bar color
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        return hwp_create_chart(
            chart_type="bar",
            data={
                "labels": labels,
                "datasets": [{"label": bar_label or "Data", "data": values}],
            },
            title=title,
            color_scheme="default",
            return_base64=return_base64,
        )

    @mcp.tool()
    def hwp_create_line_chart(
        labels: list[str],
        series: list[Dict[str, Any]],
        title: Optional[str] = None,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create line chart with multiple series.

        Args:
            labels: X-axis labels
            series: Data series list [{"label": "...", "data": [...]}]
            title: Chart title
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        return hwp_create_chart(
            chart_type="line",
            data={"labels": labels, "datasets": series},
            title=title,
            return_base64=return_base64,
        )

    @mcp.tool()
    def hwp_create_pie_chart(
        labels: list[str],
        values: list[float],
        title: Optional[str] = None,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Create pie chart.

        Args:
            labels: Pie slice labels
            values: Values for each slice
            title: Chart title
            return_base64: Return Base64 image

        Returns:
            dict: Creation result
        """
        return hwp_create_chart(
            chart_type="pie",
            data={"labels": labels, "datasets": [{"label": "Ratio", "data": values}]},
            title=title,
            color_scheme="pastel",
            return_base64=return_base64,
        )

    @mcp.tool()
    def hwp_get_chart_types() -> Dict[str, Any]:
        """
        Get list of supported chart types.

        Returns:
            dict: Chart type information
        """
        return {
            "supported_types": [
                {
                    "type": "bar",
                    "name": "Bar Chart",
                    "description": "Compare values with bars",
                    "best_for": "Category comparison, time series",
                },
                {
                    "type": "line",
                    "name": "Line Chart",
                    "description": "Show trends with lines",
                    "best_for": "Time series, trend analysis",
                },
                {
                    "type": "pie",
                    "name": "Pie Chart",
                    "description": "Show proportions as circle",
                    "best_for": "Ratio comparison, composition",
                },
                {
                    "type": "area",
                    "name": "Area Chart",
                    "description": "Fill area under line",
                    "best_for": "Cumulative trends, emphasis",
                },
                {
                    "type": "scatter",
                    "name": "Scatter Plot",
                    "description": "Display points",
                    "best_for": "Correlation, distribution",
                },
                {
                    "type": "histogram",
                    "name": "Histogram",
                    "description": "Show value distribution",
                    "best_for": "Distribution analysis, frequency",
                },
            ],
            "color_schemes": ["default", "pastel", "dark", "monochrome"],
            "output_formats": ["base64"],
        }
