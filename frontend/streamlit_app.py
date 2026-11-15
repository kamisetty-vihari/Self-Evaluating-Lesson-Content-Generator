import sys
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

# `streamlit run frontend/streamlit_app.py` starts from the frontend folder.
# Add the project root so this UI can import shared backend configuration.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Streamlit is a separate process from FastAPI, so it loads `.env` independently.
load_dotenv()
from backend.config import BACKEND_URL
st.set_page_config(page_title="Lesson Generator", page_icon="📚")
st.title("Self-Evaluating Lesson Generator")
st.caption("Each draft is evaluated against a strict rubric and regenerated up to two times.")
is_generating = st.session_state.get("is_generating", False)
with st.form("lesson"):
    topic = st.text_input("Topic", disabled=is_generating)
    audience = st.selectbox("Audience", ["beginner", "intermediate", "advanced"], disabled=is_generating)
    duration = st.slider("Minutes", 5, 90, 20, disabled=is_generating)
    submitted = st.form_submit_button("Generating..." if is_generating else "Generate lesson", disabled=is_generating)

if submitted:
    # Rerun into a locked state before making the slow local-model request.
    st.session_state["pending_lesson"] = {"topic": topic, "audience": audience, "duration_minutes": duration}
    st.session_state["is_generating"] = True
    st.session_state.pop("latest_result", None)
    st.session_state.pop("latest_error", None)
    st.rerun()

if st.session_state.get("is_generating"):
    st.info("Generating your lesson. Lesson inputs are disabled until the result is ready.")
    try:
        response = requests.post(f"{BACKEND_URL}/lessons", json=st.session_state["pending_lesson"], timeout=600)
        response.raise_for_status()
        st.session_state["latest_result"] = response.json()
    except requests.RequestException as error:
        st.session_state["latest_error"] = str(error)
    finally:
        # Always unlock the form, including if the backend request times out or fails.
        st.session_state["is_generating"] = False
        st.session_state.pop("pending_lesson", None)
    # Render again after unlocking so the form controls are enabled immediately.
    st.rerun()

if latest_error := st.session_state.get("latest_error"):
    st.error(f"Backend request failed: {latest_error}")

if result := st.session_state.get("latest_result"):
    st.success(f"{result['status'].title()} after {result['attempts']} attempt(s), score {result['evaluation']['score']}/100")
    st.write(result["evaluation"]["feedback"])
    st.markdown(result["lesson"])
st.subheader("Lesson history")
try:
    # Fetch on every rerun so newly completed lessons appear without a refresh button.
    response = requests.get(f"{BACKEND_URL}/runs", timeout=10)
    response.raise_for_status()
    st.session_state["runs"] = response.json()
except requests.RequestException as error:
    st.info(f"History is unavailable until the backend is running: {error}")

for run in st.session_state.get("runs", []):
    label = f"#{run['id']} — {run['topic']} ({run['status']}, {run['attempts']} attempt(s))"
    with st.expander(label):
        st.caption(f"Created: {run['created_at']}")
        if st.button("View lesson output", key=f"view-run-{run['id']}"):
            try:
                response = requests.get(f"{BACKEND_URL}/runs/{run['id']}", timeout=20)
                response.raise_for_status()
                st.session_state["selected_run"] = response.json()
            except requests.RequestException as error:
                st.error(f"Could not retrieve this lesson: {error}")

selected_run = st.session_state.get("selected_run")
if selected_run:
    st.subheader(f"Saved lesson #{selected_run['run_id']}")
    st.write(f"Final score: {selected_run['evaluation']['score']}/100")
    st.write(selected_run["evaluation"]["feedback"])
    st.markdown(selected_run["lesson"])
