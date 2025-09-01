# streamlit_dashboard.py
import streamlit as st
import requests
import pandas as pd

# --- Configuration ---
FLASK_BACKEND_URL = "http://localhost:5000"

st.set_page_config(layout="wide", page_title="AI-Powered Resume Screener Dashboard", page_icon="📝")

# --- Helper Functions (API calling functions are unchanged) ---
def call_batch_screen_api(job_description, uploaded_files, strictness, positive_factors, negative_factors):
    files = [("resumes[]", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
    data = {
        "job_description": job_description, "strictness": strictness,
        "positive_factors": positive_factors, "negative_factors": negative_factors
    }
    try:
        response = requests.post(f"{FLASK_BACKEND_URL}/batch_screen", files=files, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        return None

def process_single_resume(job_description, uploaded_file, strictness, positive_factors, negative_factors):
    files = {"resume": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    data = {
        "job_description": job_description, "strictness": strictness,
        "positive_factors": positive_factors, "negative_factors": negative_factors
    }
    try:
        response = requests.post(f"{FLASK_BACKEND_URL}/screen", files=files, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error processing single resume: {e}")
        return None

def call_recommend_api(candidate_scores, num_recommendations):
    headers = {'Content-Type': 'application/json'}
    data = {"candidate_scores": candidate_scores, "num_recommendations": num_recommendations}
    try:
        response = requests.post(f"{FLASK_BACKEND_URL}/recommend", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting recommendations: {e}")
        return None

def call_module_api(module_name, payload):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(f"{FLASK_BACKEND_URL}/module/{module_name}", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling {module_name} module: {e}")
        return None

# --- UPDATED Display Functions ---
def display_results_table(results):
    """Displays batch processing results in a simplified table."""
    data = []
    for item in results:
        row = {"Filename": item["filename"]}
        if "score" in item:
            score = item["score"]
            row["Name"] = score.get("name", "N/A")
            row["Aggregate Score"] = f"{score.get('aggregate_score', 0):.2f}"
            row["Technical"] = score.get("technical_score", 0)
            row["Soft Skills"] = score.get("softskills_score", 0)
            row["Experience & Align"] = score.get("experience_and_alignment_score", 0) # UPDATED
            # Data for expander
            row["details"] = score
        elif "error" in item:
            row["Status"] = "Error"
            row["details"] = {"error": item.get("error", "Unknown")}
        data.append(row)

    df = pd.DataFrame(data)
    if df.empty:
        st.info("No results to display yet.")
        return

    st.markdown("### Processed Resumes")
    # Using st.data_editor to create a selectable table
    df.insert(0, 'Select', False)
    edited_df = st.data_editor(
        df.drop(columns=['details']), # Don't show the details dict in the table
        column_config={"Select": st.column_config.CheckboxColumn("Select", help="Select candidates for module processing", default=False)},
        hide_index=True, use_container_width=True, key="processed_resumes_editor"
    )

    selected_filenames = edited_df[edited_df.Select]["Filename"].tolist()
    st.session_state.selected_candidates = [
        item for item in results if item["filename"] in selected_filenames and "score" in item
    ]
    
    # Expander for details
    for _, row in df.iterrows():
        with st.expander(f"Details for {row['Filename']}: {row.get('Name', '')}"):
            details = row['details']
            if "error" in details:
                st.error(f"Error: {details['error']}")
            else:
                st.write(f"**Technical:** Score {details['technical_score']} - *{details['technical_reason']}*")
                st.write(f"**Soft Skills:** Score {details['softskills_score']} - *{details['softskills_reason']}*")
                st.write(f"**Experience & Alignment:** Score {details['experience_and_alignment_score']} - *{details['experience_and_alignment_reason']}*")
                if details.get('positive_highlights'):
                    st.success(f"**Positive Highlight:** {details['positive_highlights']}")
                if details.get('negative_highlights'):
                    st.warning(f"**Negative Highlight:** {details['negative_highlights']}")

# --- Streamlit UI ---
st.title("AI-Powered Resume Screener 🚀")

# Sidebar for inputs
with st.sidebar:
    st.header("Job & Settings")
    job_description = st.text_area("Job Description", "Looking for a Python Developer...", height=250)
    st.subheader("Fine-Tune Scoring")
    positive_factors = st.text_area("Positive Factors (Reward for...)", placeholder="e.g., GCP certification, fintech experience")
    negative_factors = st.text_area("Negative Factors (Penalize for...)", placeholder="e.g., No SQL experience, job gaps > 6 months")
    strictness_level = st.selectbox("Screening Strictness", ["low", "medium", "high", "very strict"], index=1)
    st.markdown("---")
    uploaded_files = st.file_uploader("Upload PDF Resumes", type="pdf", accept_multiple_files=True)
    
    process_button = st.button("Process Resumes", disabled=not uploaded_files)

# Initialize session states
if 'raw_results' not in st.session_state: st.session_state.raw_results = []
if 'selected_candidates' not in st.session_state: st.session_state.selected_candidates = []

# Processing Logic
if process_button:
    with st.spinner(f"Processing {len(uploaded_files)} resumes..."):
        st.session_state.selected_candidates = [] # Clear selection on new run
        if len(uploaded_files) == 1:
            result = process_single_resume(job_description, uploaded_files[0], strictness_level, positive_factors, negative_factors)
            if result:
                resume_content_bytes = uploaded_files[0].getvalue()
                st.session_state.raw_results = [{"filename": uploaded_files[0].name, "score": result, "resume_content": resume_content_bytes.decode('latin-1')}]
        else:
            st.session_state.raw_results = call_batch_screen_api(job_description, uploaded_files, strictness_level, positive_factors, negative_factors)
        
        if not st.session_state.raw_results:
            st.error("Processing failed. Please check backend logs.")

# Main content area
st.subheader("Screening Results")
if st.session_state.raw_results:
    display_results_table(st.session_state.raw_results)

    # Recommendations Section
    with st.container(border=True):
        st.subheader("Candidate Recommendations")
        successful_scores = [item["score"] for item in st.session_state.raw_results if "score" in item]
        if successful_scores:
            num_reco = st.slider("Number of recommendations:", 1, len(successful_scores), min(3, len(successful_scores)))
            if st.button("Get Recommendations"):
                with st.spinner("Generating recommendations..."):
                    recos = call_recommend_api(successful_scores, num_reco)
                    if recos and "recommendations" in recos:
                        for rec in recos["recommendations"]:
                            st.markdown(f"**- {rec['name']} (Score: {rec['score']:.2f}):** {rec['reason']}")
        else:
            st.info("No successfully scored candidates to recommend.")

# Module Analysis Section
if st.session_state.selected_candidates:
    st.subheader(f"Deeper Analysis for {len(st.session_state.selected_candidates)} Selected Candidate(s)")
    
    candidate_options = {f"{s['score']['name']} ({s['filename']})": s for s in st.session_state.selected_candidates}
    selected_candidate_str = st.selectbox("Choose a candidate to analyze:", candidate_options.keys())
    
    if selected_candidate_str:
        selected_candidate_data = candidate_options[selected_candidate_str]
        resume_content_str = selected_candidate_data['resume_content']
        
        st.markdown("##### Run Analysis Modules")
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("🚨 Red Flags", use_container_width=True):
            payload = {"resume_content": resume_content_str}
            with st.spinner("Detecting red flags..."):
                result = call_module_api("red_flags", payload)
                if result:
                    if result.get('red_flags_found'): st.error(result.get('summary'))
                    else: st.success(result.get('summary'))
                        
        if col2.button("💰 Salary Est.", use_container_width=True):
            payload = {"job_description": job_description, "resume_content": resume_content_str}
            with st.spinner("Estimating salary..."):
                result = call_module_api("salary_estimation", payload)
                if result:
                    st.info(f"**Range:** {result.get('estimated_salary_range')}")
                    st.write(result.get('summary'))

        if col3.button("✅ Consistency", use_container_width=True):
            payload = {"resume_content": resume_content_str}
            with st.spinner("Checking consistency..."):
                result = call_module_api("background_consistency", payload)
                if result:
                    if result.get('inconsistencies_found'): st.error(result.get('summary'))
                    else: st.success(result.get('summary'))

        if col4.button("🎯 Fit Score", use_container_width=True):
            payload = {"job_description": job_description, "resume_content": resume_content_str}
            with st.spinner("Calculating fit score..."):
                result = call_module_api("candidate_fit", payload)
                if result:
                    st.info(f"**Role Fit:** {result.get('role_fit_score')}/10 | **Culture Fit:** {result.get('culture_fit_score')}/10")
                    st.write(result.get('summary'))