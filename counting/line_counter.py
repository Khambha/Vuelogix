
import logging
import math

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from tracking.tracker import TrackedPerson


logger = logging.getLogger(__name__)

Point = Tuple[float, float]


@dataclass
class TrackState:
    last_point: Point
    last_stable_point: Optional[Point]
    stable_side: Optional[int]
    last_seen_frame: int


class LineCounter:

    def __init__(
        self,
        point_a: Point,
        point_b: Point,
        hysteresis_distance: float = 8.0,
        max_missing_frames: int = 120
    ):

        if point_a == point_b:
            raise ValueError(
                "Counting line endpoints must be different."
            )

        if hysteresis_distance < 0:
            raise ValueError(
                "Hysteresis distance cannot be negative."
            )

        if max_missing_frames < 1:
            raise ValueError(
                "max_missing_frames must be at least 1."
            )

        self.point_a = point_a
        self.point_b = point_b

        self.hysteresis_distance = hysteresis_distance
        self.max_missing_frames = max_missing_frames

        self.line_length = math.dist(
            self.point_a,
            self.point_b
        )

        self.track_states: Dict[int, TrackState] = {}

        self.a_to_b_count = 0
        self.b_to_a_count = 0

        self.frame_number = 0

    # --------------------------------------------------
    # UPDATE COUNTING LINE
    # --------------------------------------------------

    def set_line(
        self,
        point_a: Point,
        point_b: Point
    ) -> None:

        if point_a == point_b:
            raise ValueError(
                "Counting line endpoints must be different."
            )

        new_length = math.dist(
            point_a,
            point_b
        )

        if new_length <= 0:
            raise ValueError(
                "Counting line must have a positive length."
            )

        self.point_a = point_a
        self.point_b = point_b
        self.line_length = new_length

        # Clear old track positions to prevent accidental
        # crossings caused by moving the counting line.
        # Existing accumulated counts are preserved.
        self.track_states.clear()

        logger.info(
            "Counting line updated: A=%s, B=%s",
            self.point_a,
            self.point_b
        )

    # --------------------------------------------------
    # 1. CALCULATE SIGNED DISTANCE FROM COUNTING LINE
    # --------------------------------------------------

    def _signed_distance(self, point: Point) -> float:

        ax, ay = self.point_a
        bx, by = self.point_b

        px, py = point

        cross_product = (
            (bx - ax) * (py - ay)
            - (by - ay) * (px - ax)
        )

        return cross_product / self.line_length

    # --------------------------------------------------
    # 2. DETERMINE WHICH SIDE A PERSON IS ON
    # --------------------------------------------------

    def _get_stable_side(self, point: Point) -> Optional[int]:

        distance = self._signed_distance(point)

        if distance > self.hysteresis_distance:
            return 1

        if distance < -self.hysteresis_distance:
            return -1

        return None

    # --------------------------------------------------
    # 3. GEOMETRY: SEGMENT ORIENTATION
    # --------------------------------------------------

    @staticmethod
    def _orientation(
        p1: Point,
        p2: Point,
        p3: Point
    ) -> float:

        return (
            (p2[0] - p1[0]) * (p3[1] - p1[1])
            - (p2[1] - p1[1]) * (p3[0] - p1[0])
        )

    # --------------------------------------------------
    # 4. CHECK WHETHER A POINT LIES ON A SEGMENT
    # --------------------------------------------------

    @staticmethod
    def _on_segment(
        a: Point,
        b: Point,
        p: Point,
        epsilon: float = 1e-9
    ) -> bool:

        return (
            min(a[0], b[0]) - epsilon
            <= p[0]
            <= max(a[0], b[0]) + epsilon

            and

            min(a[1], b[1]) - epsilon
            <= p[1]
            <= max(a[1], b[1]) + epsilon
        )

    # --------------------------------------------------
    # 5. CHECK WHETHER TWO LINE SEGMENTS INTERSECT
    # --------------------------------------------------

    @classmethod
    def _segments_intersect(
        cls,
        p1: Point,
        p2: Point,
        q1: Point,
        q2: Point
    ) -> bool:

        epsilon = 1e-9

        o1 = cls._orientation(p1, p2, q1)
        o2 = cls._orientation(p1, p2, q2)

        o3 = cls._orientation(q1, q2, p1)
        o4 = cls._orientation(q1, q2, p2)

        if (
            ((o1 > epsilon and o2 < -epsilon)
             or (o1 < -epsilon and o2 > epsilon))

            and

            ((o3 > epsilon and o4 < -epsilon)
             or (o3 < -epsilon and o4 > epsilon))
        ):
            return True

        if abs(o1) <= epsilon and cls._on_segment(p1, p2, q1):
            return True

        if abs(o2) <= epsilon and cls._on_segment(p1, p2, q2):
            return True

        if abs(o3) <= epsilon and cls._on_segment(q1, q2, p1):
            return True

        if abs(o4) <= epsilon and cls._on_segment(q1, q2, p2):
            return True

        return False

    # --------------------------------------------------
    # 6. VALIDATE CROSSING OF THE FINITE COUNTING LINE
    # --------------------------------------------------

    def _is_valid_crossing(
        self,
        previous_stable_point: Point,
        current_point: Point
    ) -> bool:

        return self._segments_intersect(
            previous_stable_point,
            current_point,
            self.point_a,
            self.point_b
        )

    # --------------------------------------------------
    # 7. UPDATE TRACKING AND COUNT CROSSINGS
    # --------------------------------------------------

    def update(self, tracked_people: List[TrackedPerson]) -> None:

        self.frame_number += 1

        for person in tracked_people:

            track_id = person.track_id
            current_point = person.bottom_center

            current_side = self._get_stable_side(
                current_point
            )

            # NEW TRACK

            if track_id not in self.track_states:

                self.track_states[track_id] = TrackState(
                    last_point=current_point,
                    last_stable_point=(
                        current_point
                        if current_side is not None
                        else None
                    ),
                    stable_side=current_side,
                    last_seen_frame=self.frame_number
                )

                continue

            # EXISTING TRACK

            state = self.track_states[track_id]

            state.last_seen_frame = self.frame_number

            # Person is inside the hysteresis zone.
            if current_side is None:

                state.last_point = current_point

                continue

            # INITIALIZE IF NO STABLE SIDE EXISTS

            if state.stable_side is None:

                state.stable_side = current_side
                state.last_stable_point = current_point
                state.last_point = current_point

                continue

            # CHECK FOR SIDE CHANGE

            if current_side != state.stable_side:

                previous_stable_point = state.last_stable_point

                if previous_stable_point is not None:

                    crossed_line = self._is_valid_crossing(
                        previous_stable_point,
                        current_point
                    )

                    if crossed_line:

                        # Negative side -> Positive side.
                        if (
                            state.stable_side == -1
                            and current_side == 1
                        ):

                            self.a_to_b_count += 1

                            logger.info(
                                "A -> B crossing | Track ID: %d | "
                                "Count: %d",
                                track_id,
                                self.a_to_b_count
                            )

                        # Positive side -> Negative side.
                        elif (
                            state.stable_side == 1
                            and current_side == -1
                        ):

                            self.b_to_a_count += 1

                            logger.info(
                                "B -> A crossing | Track ID: %d | "
                                "Count: %d",
                                track_id,
                                self.b_to_a_count
                            )

                state.stable_side = current_side

            # SAVE CURRENT STABLE POSITION

            state.last_stable_point = current_point
            state.last_point = current_point

        self._cleanup_old_tracks()

    # --------------------------------------------------
    # 8. REMOVE TRACKS THAT HAVE DISAPPEARED
    # --------------------------------------------------

    def _cleanup_old_tracks(self) -> None:

        expired_ids = [

            track_id

            for track_id, state in self.track_states.items()

            if (
                self.frame_number - state.last_seen_frame
                > self.max_missing_frames
            )
        ]

        for track_id in expired_ids:

            del self.track_states[track_id]

            logger.debug(
                "Removed expired track ID: %d",
                track_id
            )

    # --------------------------------------------------
    # 9. GET CURRENT COUNTS
    # --------------------------------------------------

    def get_counts(self) -> dict:

        return {
            "a_to_b": self.a_to_b_count,
            "b_to_a": self.b_to_a_count,
            "total": (
                self.a_to_b_count
                + self.b_to_a_count
            )
        }

    # --------------------------------------------------
    # 10. RESET COUNTERS
    # --------------------------------------------------

    def reset(self) -> None:

        self.track_states.clear()

        self.a_to_b_count = 0
        self.b_to_a_count = 0

        self.frame_number = 0

        logger.info("People counters have been reset.")
