
import unittest

from counting.line_counter import LineCounter
from tracking.tracker import TrackedPerson


class TestLineCounter(unittest.TestCase):

    def setUp(self):

        # Horizontal counting line.
        self.counter = LineCounter(
            point_a=(50, 180),
            point_b=(590, 180),
            hysteresis_distance=8,
            max_missing_frames=120
        )

    # Helper to simulate a tracked person.
    def create_person(self, track_id, x, y):

        return TrackedPerson(
            track_id=track_id,
            x1=x - 10,
            y1=y - 40,
            x2=x + 10,
            y2=y,
            confidence=0.90
        )

    # ------------------------------------------
    # TEST 1: TOP TO BOTTOM
    # ------------------------------------------

    def test_a_to_b_crossing(self):

        self.counter.update([
            self.create_person(1, 320, 150)
        ])

        self.counter.update([
            self.create_person(1, 320, 175)
        ])

        self.counter.update([
            self.create_person(1, 320, 180)
        ])

        self.counter.update([
            self.create_person(1, 320, 185)
        ])

        self.counter.update([
            self.create_person(1, 320, 210)
        ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["a_to_b"], 1)
        self.assertEqual(counts["b_to_a"], 0)
        self.assertEqual(counts["total"], 1)

    # ------------------------------------------
    # TEST 2: BOTTOM TO TOP
    # ------------------------------------------

    def test_b_to_a_crossing(self):

        self.counter.update([
            self.create_person(2, 320, 210)
        ])

        self.counter.update([
            self.create_person(2, 320, 185)
        ])

        self.counter.update([
            self.create_person(2, 320, 180)
        ])

        self.counter.update([
            self.create_person(2, 320, 175)
        ])

        self.counter.update([
            self.create_person(2, 320, 150)
        ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["a_to_b"], 0)
        self.assertEqual(counts["b_to_a"], 1)
        self.assertEqual(counts["total"], 1)

    # ------------------------------------------
    # TEST 3: CROSS AND RETURN
    # ------------------------------------------

    def test_person_crosses_and_returns(self):

        self.counter.update([
            self.create_person(3, 320, 150)
        ])

        # First crossing: top to bottom.
        self.counter.update([
            self.create_person(3, 320, 210)
        ])

        # Second crossing: bottom to top.
        self.counter.update([
            self.create_person(3, 320, 150)
        ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["a_to_b"], 1)
        self.assertEqual(counts["b_to_a"], 1)
        self.assertEqual(counts["total"], 2)

    # ------------------------------------------
    # TEST 4: PERSON STAYS ON ONE SIDE
    # ------------------------------------------

    def test_person_stays_on_same_side(self):

        positions = [150, 145, 140, 135, 130]

        for y in positions:

            self.counter.update([
                self.create_person(4, 320, y)
            ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["total"], 0)

    # ------------------------------------------
    # TEST 5: PERSON MOVES INSIDE HYSTERESIS ZONE
    # ------------------------------------------

    def test_person_moves_inside_hysteresis_zone(self):

        positions = [
            150,
            175,
            180,
            185,
            180,
            175,
            150
        ]

        for y in positions:

            self.counter.update([
                self.create_person(5, 320, y)
            ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["total"], 0)

    # ------------------------------------------
    # TEST 6: CROSSING OUTSIDE FINITE LINE
    # ------------------------------------------

    def test_crossing_outside_line_endpoints(self):

        # x=10 is outside the counting line,
        # which starts at x=50.
        self.counter.update([
            self.create_person(6, 10, 150)
        ])

        self.counter.update([
            self.create_person(6, 10, 210)
        ])

        counts = self.counter.get_counts()

        self.assertEqual(counts["total"], 0)


if __name__ == "__main__":

    unittest.main(verbosity=2)
