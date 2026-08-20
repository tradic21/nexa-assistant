import math


class GestureDetector:
    def distance_px(self, landmarks, point1, point2, frame_width, frame_height):
        return math.hypot(
            (landmarks[point1].x - landmarks[point2].x) * frame_width,
            (landmarks[point1].y - landmarks[point2].y) * frame_height
        )

    def is_finger_extended(self, landmarks, tip_id, pip_id, mcp_id, frame_width, frame_height):
        wrist_id = 0

        wrist_to_tip = self.distance_px(
            landmarks,
            wrist_id,
            tip_id,
            frame_width,
            frame_height
        )

        wrist_to_pip = self.distance_px(
            landmarks,
            wrist_id,
            pip_id,
            frame_width,
            frame_height
        )

        mcp_to_tip = self.distance_px(
            landmarks,
            mcp_id,
            tip_id,
            frame_width,
            frame_height
        )

        mcp_to_pip = self.distance_px(
            landmarks,
            mcp_id,
            pip_id,
            frame_width,
            frame_height
        )

        return (
            wrist_to_tip > wrist_to_pip * 1.08
            and mcp_to_tip > mcp_to_pip * 1.10
        )

    def get_hand_size(self, landmarks, frame_width, frame_height):
        # Veličina dlana: udaljenost zapešće - baza srednjeg prsta
        return self.distance_px(
            landmarks,
            0,
            9,
            frame_width,
            frame_height
        )

    def point_to_px(self, landmark, frame_width, frame_height):
        return (
            int(landmark.x * frame_width),
            int(landmark.y * frame_height)
        )

    def detect(self, landmarks, frame_width, frame_height):
        """
        Prima MediaPipe landmarks i vraća naziv prepoznate geste
        te dodatne točke koje worker koristi za izvršavanje akcija.
        """

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]

        thumb_x, thumb_y = self.point_to_px(
            thumb_tip,
            frame_width,
            frame_height
        )

        index_x, index_y = self.point_to_px(
            index_tip,
            frame_width,
            frame_height
        )

        thumb_pos = (thumb_x, thumb_y)
        index_pos = (index_x, index_y)

        hand_size = self.get_hand_size(
            landmarks,
            frame_width,
            frame_height
        )

        if hand_size < 20:
            return {
                "gesture": "Gesture not recognized",
                "thumb_pos": thumb_pos,
                "index_pos": index_pos
            }

        index_up = self.is_finger_extended(
            landmarks,
            8,
            6,
            5,
            frame_width,
            frame_height
        )

        middle_up = self.is_finger_extended(
            landmarks,
            12,
            10,
            9,
            frame_width,
            frame_height
        )

        ring_up = self.is_finger_extended(
            landmarks,
            16,
            14,
            13,
            frame_width,
            frame_height
        )

        pinky_up = self.is_finger_extended(
            landmarks,
            20,
            18,
            17,
            frame_width,
            frame_height
        )

        thumb_to_index_base = self.distance_px(
            landmarks,
            4,
            5,
            frame_width,
            frame_height
        )

        thumb_to_wrist = self.distance_px(
            landmarks,
            4,
            0,
            frame_width,
            frame_height
        )

        thumb_ip_to_wrist = self.distance_px(
            landmarks,
            3,
            0,
            frame_width,
            frame_height
        )

        thumb_out = (
            thumb_to_index_base > hand_size * 0.55
            and thumb_to_wrist > thumb_ip_to_wrist * 1.10
        )

        fist_gesture = (
            not index_up
            and not middle_up
            and not ring_up
            and not pinky_up
            and not thumb_out
        )

        shaka_gesture = (
            thumb_out
            and pinky_up
            and not index_up
            and not middle_up
            and not ring_up
        )

        pinch_distance = self.distance_px(
            landmarks,
            4,
            8,
            frame_width,
            frame_height
        )

        pinch_volume_gesture = (
            pinch_distance < hand_size * 0.28
            and index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        )

        pinch_brightness_gesture = (
            pinch_distance < hand_size * 0.28
            and index_up
            and middle_up
            and ring_up
            and pinky_up
        )

        index_middle_distance = self.distance_px(
            landmarks,
            8,
            12,
            frame_width,
            frame_height
        )

        double_click_gesture = (
            index_up
            and middle_up
            and not ring_up
            and not pinky_up
            and index_middle_distance < hand_size * 0.30
        )

        # Točke koje se koriste za različite akcije
        move_point = landmarks[9]
        move_pos = self.point_to_px(
            move_point,
            frame_width,
            frame_height
        )

        scroll_point = landmarks[9]
        scroll_pos = self.point_to_px(
            scroll_point,
            frame_width,
            frame_height
        )

        drag_point = landmarks[9]
        drag_pos = self.point_to_px(
            drag_point,
            frame_width,
            frame_height
        )

        pinch_pos = index_pos

        base_data = {
            "thumb_pos": thumb_pos,
            "index_pos": index_pos,
            "move_pos": move_pos,
            "scroll_pos": scroll_pos,
            "drag_pos": drag_pos,
            "pinch_pos": pinch_pos,
            "hand_size": hand_size
        }

        if (
            index_up
            and middle_up
            and ring_up
            and pinky_up
            and pinch_distance > hand_size * 0.48
        ):
            return {
                **base_data,
                "gesture": "NEUTRAL"
            }

        elif fist_gesture:
            return {
                **base_data,
                "gesture": "DRAG"
            }
        
        elif pinch_volume_gesture:
            return {
                **base_data,
                "gesture": "PINCH VOLUME"
            }

        elif pinch_brightness_gesture:
            return {
                **base_data,
                "gesture": "PINCH BRIGHTNESS"
            }
   

        elif index_up and middle_up and ring_up and not pinky_up:
            return {
                **base_data,
                "gesture": "SCROLL"
            }

        elif double_click_gesture:
            return {
                **base_data,
                "gesture": "DOUBLE CLICK"
            }

        elif index_up and middle_up and not ring_up and not pinky_up:
            return {
                **base_data,
                "gesture": "MOVE"
            }

        elif index_up and not middle_up and not ring_up and not pinky_up:
            return {
                **base_data,
                "gesture": "LEFT CLICK"
            }

        elif shaka_gesture:
            return {
                **base_data,
                "gesture": "RIGHT CLICK"
            }

        else:
            return {
                **base_data,
                "gesture": "Gesture not recognized"
            }