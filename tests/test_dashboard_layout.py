import unittest

from activesg_gym_analytics.dashboard import INDEX_HTML


class DashboardLayoutTests(unittest.TestCase):
    def test_heatmap_container_tracks_plot_height(self):
        self.assertIn("chart.style.height=height+'px'", INDEX_HTML)

    def test_long_gym_labels_use_plotly_automargins(self):
        self.assertGreaterEqual(INDEX_HTML.count("yaxis:{automargin:true"), 2)

    def test_chart_panels_can_shrink_on_mobile(self):
        self.assertIn(".panel{min-width:0;", INDEX_HTML)
        self.assertIn(".chart{width:100%;min-width:0;", INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
