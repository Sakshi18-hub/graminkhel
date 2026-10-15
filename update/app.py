"""GraminKhel - run with: python -m streamlit run app.py"""
import mediapipe as mp  # must load first on Windows (avoids DLL error)
import cv2
import random, tempfile
import plotly.express as px
import streamlit as st
from core import db
from core.jump import analyze_jump, analyze_broad_jump, analyze_sprint
from core.scoring import talent_score, percentile, age_band, age_ok, AGE_MIN, AGE_MAX

st.set_page_config(page_title="GraminKhel", page_icon="🏃", layout="wide")
st.title("🏃 GraminKhel - Rural Sports Talent Discovery")
page = st.sidebar.radio("Go to", ["Athlete Test", "Scout Dashboard", "About"])

def run_video(upload, fn, *args):
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(upload.read())
    return fn(f.name, *args)

if page == "Athlete Test":
    st.subheader("1. Athlete details")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Name")
    age = c2.number_input(f"Age ({AGE_MIN}-{AGE_MAX} allowed)", 1, 99, 15)
    gender = c3.selectbox("Gender (as in school records)", ["Male", "Female"])
    c4, c5, c6 = st.columns(3)
    village = c4.text_input("Village"); district = c5.text_input("District")
    sport = c6.selectbox("Sport interest", ["Athletics", "Kabaddi", "Football", "Kho-Kho", "Other"])
    height = st.number_input("Height (cm) - measured by coordinator", 100, 210, 165)
    id_ok = st.checkbox("Coordinator confirms age and gender from school ID / records")

    if "code" not in st.session_state:
        st.session_state.code = str(random.randint(1000, 9999))
    st.info(f"🔐 Anti-cheat code: **{st.session_state.code}**. Hold it up at the start of each "
            "video. One athlete only in the frame, one continuous take.")

    st.subheader("2. Tests")
    st.caption("Video tests: full body visible, steady camera, at least 480p, 2-20 seconds, "
               "stand still 1-2 seconds first. Broad jump and sprint: SIDE view.")
    jv = st.file_uploader("Vertical jump video", type=["mp4", "mov"], key="j")
    bv = st.file_uploader("Standing broad jump video (side view)", type=["mp4", "mov"], key="b")
    sv = st.file_uploader("30 m sprint video (side view)", type=["mp4", "mov"], key="s")
    m1, m2 = st.columns(2)
    shuttle = m1.number_input("4x10 m shuttle run time (s, stopwatch, 0 = skip)", 0.0, 40.0, 0.0, 0.1)
    run = m2.number_input("1.6 km run time (min, stopwatch, 0 = skip)", 0.0, 30.0, 0.0, 0.1)

    if st.button("Analyze & Save", type="primary"):
        if not name:
            st.warning("Enter the athlete's name."); st.stop()
        if not age_ok(age):
            st.error(f"Age must be between {AGE_MIN} and {AGE_MAX} for this screening."); st.stop()
        if not id_ok:
            st.error("Coordinator must confirm age and gender from school records first."); st.stop()
        res, warns = {}, []
        try:
            for up, fn, args, key in ((jv, analyze_jump, (height,), "jump"),
                                      (bv, analyze_broad_jump, (height,), "broad"),
                                      (sv, analyze_sprint, (), "sprint")):
                if up:
                    res[key] = run_video(up, fn, *args)
                    warns += res[key]["warnings"]
        except ValueError as e:
            st.error(str(e)); st.stop()
        jump = res.get("jump", {}).get("jump_cm"); broad = res.get("broad", {}).get("broad_cm")
        sprint = res.get("sprint", {}).get("time_s")
        shuttle_v = shuttle or None; run_v = run or None
        if all(v is None for v in (jump, broad, sprint, shuttle_v, run_v)):
            st.warning("Add at least one test."); st.stop()
        score = talent_score(gender, age, jump, sprint, broad, shuttle_v, run_v)
        peers = db.all_athletes()
        peers = peers[(peers.gender == gender) & (peers.age.apply(age_band) == age_band(age))]
        pct = percentile(score, peers.score.tolist())
        db.add_athlete(name=name, age=int(age), gender=gender, village=village, district=district,
                       sport=sport, height_cm=float(height), jump_cm=jump, sprint_s=sprint,
                       broad_cm=broad, shuttle_s=shuttle_v, run_min=run_v, score=score,
                       percentile=pct, verify_code=st.session_state.code,
                       flags="; ".join(warns), id_checked=1)
        st.success("Saved!")
        for w in warns:
            st.warning("⚠️ " + w)
        a, b, c, d = st.columns(4)
        a.metric("Vertical jump (cm)", jump if jump is not None else "-")
        b.metric("Broad jump (cm)", broad if broad is not None else "-")
        c.metric("30 m sprint (s)", sprint if sprint is not None else "-")
        d.metric("Talent Score", score, f"Top {round(100 - pct)}% of peers")
        if "jump" in res:
            st.caption(f"Jump = {res['jump']['relative_pct']}% of body height. Flight-time cross-check: "
                       f"{res['jump']['flight_cm']} cm")
        st.session_state.code = str(random.randint(1000, 9999))

elif page == "Scout Dashboard":
    df = db.all_athletes()
    if df.empty:
        st.warning("No data yet. Run `python -m core.seed` for demo data."); st.stop()
    f1, f2, f3, f4 = st.columns(4)
    sports = f1.multiselect("Sport", sorted(df.sport.dropna().unique()))
    dists = f2.multiselect("District", sorted(df.district.dropna().unique()))
    gen = f3.multiselect("Gender", ["Male", "Female"])
    min_score = f4.slider("Min score", 0, 100, 0)
    if sports: df = df[df.sport.isin(sports)]
    if dists: df = df[df.district.isin(dists)]
    if gen: df = df[df.gender.isin(gen)]
    df = df[df.score >= min_score].sort_values("score", ascending=False)
    k1, k2, k3 = st.columns(3)
    k1.metric("Athletes", len(df)); k2.metric("Districts", df.district.nunique())
    k3.metric("Female share", f"{round(100 * (df.gender == 'Female').mean())}%" if len(df) else "-")
    st.subheader("🏆 Leaderboard")
    cols = ["id", "name", "age", "gender", "village", "district", "sport", "jump_cm", "broad_cm",
            "sprint_s", "shuttle_s", "run_min", "score", "verified", "id_checked", "flags"]
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True)
    a, b = st.columns(2)
    a.plotly_chart(px.bar(df.groupby("district").score.mean().reset_index(),
                          x="district", y="score", title="Avg talent score by district"), use_container_width=True)
    b.plotly_chart(px.scatter(df, x="jump_cm", y="sprint_s", color="gender",
                              hover_name="name", title="Jump vs sprint"), use_container_width=True)
    st.subheader("✅ Verify an athlete (after in-person re-test)")
    vid = st.number_input("Athlete ID", 1, step=1)
    if st.button("Mark verified"):
        db.set_verified(int(vid)); st.success("Verified")

else:
    st.markdown("""
**Problem:** Rural talent can't reach camps and trials.
**Solution:** Phone video -> pose AI -> verified, ranked talent profile -> scouts.
**Roadmap:** offline mobile app, regional voice UI, live in-app recording, cloud database.
""")
