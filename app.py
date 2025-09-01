# app.py
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import io
from flask_cors import CORS
from pydantic import ValidationError

# Assuming process_resume_from_bytes and other models are in resume_filter.py
from resume_filter import (
    process_resume_from_bytes, ResumeScore, get_recommendations, RecommendationList,
    detect_red_flags, RedFlags, estimate_salary, SalaryEstimation,
    check_background_consistency, ConsistencyCheck, calculate_fit_score, FitScore,
    extract_text_from_pdf # Import for module processing
)


app = Flask(__name__)
CORS(app)

@app.route('/ping', methods=['GET'])
def ping():
    """Simple health check endpoint."""
    return 'Server is alive!', 200

@app.route('/screen', methods=['POST'])
def screen_resume():
    """
    API endpoint to screen a single resume.
    Expects a PDF file under 'resume' and a 'job_description' string.
    Optional 'strictness', 'positive_factors', and 'negative_factors' parameters.
    """
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    if 'job_description' not in request.form:
        return jsonify({"error": "No job description provided"}), 400

    resume_file = request.files['resume']
    job_description_prompt = request.form['job_description']
    strictness_level = request.form.get('strictness', 'medium')
    positive_factors = request.form.get('positive_factors', '') # NEW
    negative_factors = request.form.get('negative_factors', '') # NEW

    if resume_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if resume_file:
        resume_content = resume_file.read()

        try:
            # UPDATED: Pass new factors to the processing function
            result: ResumeScore = process_resume_from_bytes(
                job_description_prompt,
                resume_content,
                strictness_level,
                positive_factors,
                negative_factors
            )
            return jsonify(result.model_dump()), 200
        except ValidationError as e:
            return jsonify({"error": "Data validation error from LLM output", "details": e.errors()}), 500
        except Exception as e:
            return jsonify({"error": f"An error occurred during resume screening: {str(e)}"}), 500
    return jsonify({"error": "Something went wrong during file upload processing"}), 500


@app.route('/batch_screen', methods=['POST'])
def batch_screen_resumes():
    """
    API endpoint to screen multiple resumes in a batch.
    Expects multiple PDF files under 'resumes[]' and a 'job_description' string.
    Optional 'strictness', 'positive_factors', and 'negative_factors' parameters.
    """
    if 'resumes[]' not in request.files:
        return jsonify({"error": "No resume files provided"}), 400
    if 'job_description' not in request.form:
        return jsonify({"error": "No job description provided"}), 400

    resume_files = request.files.getlist('resumes[]')
    job_description_prompt = request.form['job_description']
    strictness_level = request.form.get('strictness', 'medium')
    positive_factors = request.form.get('positive_factors', '') # NEW
    negative_factors = request.form.get('negative_factors', '') # NEW

    if not resume_files:
        return jsonify({"error": "No selected files"}), 400

    results = []
    for resume_file in resume_files:
        filename = secure_filename(resume_file.filename)
        try:
            resume_content = resume_file.read()
            # UPDATED: Pass new factors to the processing function
            score: ResumeScore = process_resume_from_bytes(
                job_description_prompt,
                resume_content,
                strictness_level,
                positive_factors,
                negative_factors
            )
            # Storing content as latin-1 string for JSON serialization to pass to modules
            results.append({"filename": filename, "score": score.model_dump(), "resume_content": resume_content.decode('latin-1')})
        except ValidationError as e:
            results.append({"filename": filename, "error": "Data validation error from LLM output", "details": e.errors()})
        except Exception as e:
            results.append({"filename": filename, "error": f"Error processing resume: {str(e)}"})

    return jsonify(results), 200

# --- Other Endpoints (Unchanged) ---

@app.route('/recommend', methods=['POST'])
def recommend_candidates():
    data = request.json
    if not data or 'candidate_scores' not in data or 'num_recommendations' not in data:
        return jsonify({"error": "Invalid request body. Expected 'candidate_scores' and 'num_recommendations'."}), 400
    try:
        recommendations: RecommendationList = get_recommendations(data['candidate_scores'], data['num_recommendations'])
        return jsonify(recommendations.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred during recommendation generation: {str(e)}"}), 500

@app.route('/module/red_flags', methods=['POST'])
def red_flags_detector():
    data = request.json
    if not data or 'resume_content' not in data:
        return jsonify({"error": "Invalid request body. Expected 'resume_content'."}), 400
    resume_content_bytes = data['resume_content'].encode('latin-1')
    try:
        resume_text = extract_text_from_pdf(io.BytesIO(resume_content_bytes))
        if not resume_text: return jsonify({"error": "Could not extract text."}), 400
        red_flags: RedFlags = detect_red_flags(resume_text)
        return jsonify(red_flags.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/module/salary_estimation', methods=['POST'])
def salary_estimation_module():
    data = request.json
    if not data or 'job_description' not in data or 'resume_content' not in data:
        return jsonify({"error": "Invalid request body."}), 400
    resume_content_bytes = data['resume_content'].encode('latin-1')
    try:
        resume_text = extract_text_from_pdf(io.BytesIO(resume_content_bytes))
        if not resume_text: return jsonify({"error": "Could not extract text."}), 400
        salary_estimate: SalaryEstimation = estimate_salary(data['job_description'], resume_text)
        return jsonify(salary_estimate.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/module/background_consistency', methods=['POST'])
def background_consistency_checker():
    data = request.json
    if not data or 'resume_content' not in data:
        return jsonify({"error": "Invalid request body."}), 400
    resume_content_bytes = data['resume_content'].encode('latin-1')
    try:
        resume_text = extract_text_from_pdf(io.BytesIO(resume_content_bytes))
        if not resume_text: return jsonify({"error": "Could not extract text."}), 400
        consistency_check: ConsistencyCheck = check_background_consistency(resume_text)
        return jsonify(consistency_check.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/module/candidate_fit', methods=['POST'])
def candidate_fit_score():
    data = request.json
    if not data or 'job_description' not in data or 'resume_content' not in data:
        return jsonify({"error": "Invalid request body."}), 400
    resume_content_bytes = data['resume_content'].encode('latin-1')
    try:
        resume_text = extract_text_from_pdf(io.BytesIO(resume_content_bytes))
        if not resume_text: return jsonify({"error": "Could not extract text."}), 400
        fit_score: FitScore = calculate_fit_score(data['job_description'], resume_text)
        return jsonify(fit_score.model_dump()), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)