"""
Tests for chart tools
"""

import pytest
from hwpx_mcp.tools.chart_tools import ChartData, ChartDataset, CreateChartInput


class TestChartSchemas:
    """Test Pydantic schemas for charts"""

    def test_chart_data_validation(self):
        """Test ChartData validation"""
        data = ChartData(
            labels=["Jan", "Feb", "Mar"],
            datasets=[ChartDataset(label="Sales", data=[100, 150, 200])],
        )
        assert len(data.labels) == 3
        assert len(data.datasets) == 1
        assert data.datasets[0].label == "Sales"

    def test_create_chart_input_validation(self):
        """Test CreateChartInput validation"""
        input_data = CreateChartInput(
            chart_type="bar",
            data=ChartData(
                labels=["A", "B", "C"],
                datasets=[ChartDataset(label="Test", data=[1, 2, 3])],
            ),
            title="Test Chart",
            width=800,
            height=600,
        )
        assert input_data.chart_type == "bar"
        assert input_data.width == 800
        assert input_data.title == "Test Chart"

    def test_invalid_chart_type(self):
        """Test invalid chart type rejection"""
        with pytest.raises(ValueError):
            CreateChartInput(
                chart_type="invalid_type",
                data=ChartData(
                    labels=["A"], datasets=[ChartDataset(label="T", data=[1])]
                ),
            )


class TestChartGenerator:
    def test_chart_types(self):
        """Test supported chart types"""
        from hwpx_mcp.tools.chart_tools import register_chart_tools

        # This test verifies the function can be imported
        assert register_chart_tools is not None
