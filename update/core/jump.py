"""Video tests: vertical jump, broad jump, sprint (with quality checks)."""
import cv2
import numpy as np
from .pose import extract_keypoints

G = 9.81
MIN_SIDE_PX, MIN_FPS, MIN_SEC, MAX_SEC = 480, 24, 2, 20

def check_video(path):
    """Reject videos that are too small, too short/long or too low fps."""
    cap = cv2.VideoCapture(path)
    w, h = int(cap.get(3)), int(cap.get(4))
    fps = cap.get(5) or 0
    n = cap.get(7) or 0
    cap.release()
    sec = n / fps if fps else 0
    if min(w, h) < MIN_SIDE_PX:
        raise ValueError(f"Video too small ({w}x{h}). Record at least 480p (720p is better).")
    if fps < MIN_FPS:
        raise ValueError(f"Video frame rate too low ({fps:.0f} fps). Need at least {MIN_FPS} fps.")
    if not (MIN_SEC <= sec <= MAX_SEC):
        raise ValueError(f"Video length {sec:.0f}s. Keep it between {MIN_SEC} and {MAX_SEC} seconds.")
    return {"w": w, "h": h, "fps": fps, "sec": sec}

def _cm_per_px(kp, height_cm, frame_h):
    """Scale from THIS athlete's own height, so a tall adult and a child
    are each converted using their own size (not a shared pixel scale)."""
    body_px = float(np.median([k["ankle_y"] - k["nose_y"] for k in kp[:15]]))
    if body_px < 0.25 * frame_h:
        raise ValueError("Athlete looks too small in the frame. Move the camera closer "
                         "so the full body fills about half of the frame height.")
    return height_cm * 0.92 / body_px

def _load(path, height_cm):
    info = check_video(path)
    kp, fps = extract_keypoints(path)
    if len(kp) < 20:
        raise ValueError("Athlete not detected. Use a full-body view and good light.")
    return info, kp, fps, _cm_per_px(kp, height_cm, info["h"])

def analyze_jump(path, height_cm):
    info, kp, fps, cm_px = _load(path, height_cm)
    hip = np.array([k["hip_y"] for k in kp])
    ank = np.array([k["ankle_y"] for k in kp])
    fr = np.array([k["frame"] for k in kp])
    peak_px = np.median(hip[:15]) - hip.min()
    jump = peak_px * cm_px
    warnings = []
    rise = np.median(ank[:15]) - ank          # ankles rise only if feet leave ground
    if rise.max() < 0.5 * peak_px:
        warnings.append("Feet may not have left the ground (ankles barely moved).")
    flight = None
    air = np.where(rise > 0.25 * rise.max())[0] if rise.max() > 0 else []
    if len(air) >= 2:
        t = (fr[air[-1]] - fr[air[0]] + 1) / fps
        flight = 100 * G * t * t / 8           # h = g*t^2/8, independent of pixel scale
        if jump > 0 and abs(flight - jump) / jump > 0.5:
            warnings.append("Pixel jump and flight-time jump disagree. Re-record with a steady camera.")
    if jump < 5 or jump > 100:
        raise ValueError(f"Unrealistic jump ({jump:.0f} cm). Please record again.")
    return {"jump_cm": round(jump, 1), "flight_cm": round(flight, 1) if flight else None,
            "relative_pct": round(jump / height_cm * 100, 1), "warnings": warnings}

def analyze_broad_jump(path, height_cm):
    """Side view. Athlete stands still, jumps forward, stays still after landing."""
    info, kp, fps, cm_px = _load(path, height_cm)
    ax = np.array([k["ankle_x"] for k in kp])
    dist = abs(np.median(ax[-10:]) - np.median(ax[:15])) * cm_px
    if dist < 40 or dist > 350:
        raise ValueError(f"Unrealistic broad jump ({dist:.0f} cm). Record side view, stand still after landing.")
    return {"broad_cm": round(dist, 1), "warnings": []}

def analyze_sprint(path, start_x=0.15, finish_x=0.85, distance_m=30):
    check_video(path)
    kp, fps = extract_keypoints(path)
    xs = np.array([k["hip_x"] for k in kp]); fr = np.array([k["frame"] for k in kp])
    s = fr[np.argmax(xs >= start_x)] if (xs >= start_x).any() else None
    f = fr[np.argmax(xs >= finish_x)] if (xs >= finish_x).any() else None
    if s is None or f is None or f <= s:
        raise ValueError("Start/finish crossing not detected.")
    t = (f - s) / fps
    return {"time_s": round(t, 2), "speed_ms": round(distance_m / t, 2), "warnings": []}
