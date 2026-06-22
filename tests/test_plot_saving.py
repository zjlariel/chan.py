from unittest.mock import Mock

from Plot.PlotDriver import CPlotDriver


def test_save2img_uses_its_own_figure():
    driver = CPlotDriver.__new__(CPlotDriver)
    driver.figure = Mock()

    driver.save2img("chart.png")

    driver.figure.savefig.assert_called_once_with("chart.png", bbox_inches="tight")
