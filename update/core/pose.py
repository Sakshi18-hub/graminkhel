"""Shared pose extraction."""
import cv2

def extract_keypoints(video_path, max_frames=900):
    import mediapipe as mp  # imported here so the rest of the app works without it
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    W = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    pose = mp.solutions.pose.Pose(model_complexity=1)
    L = mp.solutions.pose.PoseLandmark
    out, i = [], 0
    while cap.isOpened() and i < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark
            out.append({
                "frame": i,
                "nose_y": lm[L.NOSE].y * H,
                "hip_y": (lm[L.LEFT_HIP].y + lm[L.RIGHT_HIP].y) / 2 * H,
                "hip_x": (lm[L.LEFT_HIP].x + lm[L.RIGHT_HIP].x) / 2,
                "ankle_y": (lm[L.LEFT_ANKLE].y + lm[L.RIGHT_ANKLE].y) / 2 * H,
                "ankle_x": (lm[L.LEFT_ANKLE].x + lm[L.RIGHT_ANKLE].x) / 2 * W,
            })
        i += 1
    cap.release()
    pose.close()
    return out, fps
