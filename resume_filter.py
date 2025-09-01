# resume_filter.py
import json
import os
import pdfplumber
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import io

load_dotenv()

# --- Simplified Pydantic Models ---

# UPDATED: Simplified the main scoring model
class ResumeScore(BaseModel):
    name: str = Field(description="The name of the candidate found in the resume.")
    technical_score: int = Field(..., description="Score from 0–10 for technical skills.")
    technical_reason: str = Field(description="A single, succinct sentence explaining the technical score.")
    softskills_score: int = Field(..., description="Score from 0–10 for soft skills.")
    softskills_reason: str = Field(description="A single, succinct sentence explaining the soft skills score.")
    experience_and_alignment_score: int = Field(..., description="Score from 0–10 for relevant experience and alignment with employer needs.")
    experience_and_alignment_reason: str = Field(description="A single, succinct sentence explaining the experience and alignment score.")
    positive_highlights: Optional[str] = Field(None, description="A single sentence highlighting strengths based on 'Positive Factors'.")
    negative_highlights: Optional[str] = Field(None, description="A single sentence highlighting weaknesses based on 'Negative Factors'.")
    aggregate_score: float = Field(description="Overall weighted aggregate score of the resume (0-10).")

class CandidateRecommendation(BaseModel):
    name: str = Field(description="Name of the recommended candidate.")
    score: float = Field(description="Aggregate score of the candidate.")
    reason: str = Field(description="Reason for recommending this candidate.")

class RecommendationList(BaseModel):
    recommendations: List[CandidateRecommendation] = Field(description="List of recommended candidates.")

# --- UPDATED Module Models for Conciseness ---

class RedFlags(BaseModel):
    red_flags_found: bool = Field(description="True if any red flags were found, False otherwise.")
    summary: str = Field(description="A concise, single-paragraph summary (max 80 words) of any red flags detected, or a confirmation that none were found.")

class SalaryEstimation(BaseModel):
    estimated_salary_range: str = Field(description="Estimated annual salary range (e.g., '$70,000 - $90,000').")
    summary: str = Field(description="A concise, single-paragraph summary (max 80 words) justifying the salary estimation based on the candidate's profile and job description.")

class ConsistencyCheck(BaseModel):
    inconsistencies_found: bool = Field(description="True if any inconsistencies were found, False otherwise.")
    summary: str = Field(description="A concise, single-paragraph summary (max 80 words) of any background inconsistencies, or a confirmation of consistency.")

class FitScore(BaseModel):
    role_fit_score: int = Field(..., description="Score from 0-10 for role fit.")
    culture_fit_score: int = Field(..., description="Score from 0-10 for culture fit.")
    summary: str = Field(description="A concise, single-paragraph summary (max 80 words) assessing the candidate's overall fit for the role and culture.")


# --- Core Functions ---

def extract_text_from_pdf(pdf_file_object: io.BytesIO) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_file_object) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def get_llm():
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0, google_api_key=google_api_key)

# --- UPDATED Core Screening Function ---
def process_resume_from_bytes(
    job_description_prompt: str,
    resume_bytes: bytes,
    strictness_level: str = "medium",
    positive_factors: Optional[str] = None,
    negative_factors: Optional[str] = None,
) -> ResumeScore:
    llm = get_llm()
    resume_text = extract_text_from_pdf(io.BytesIO(resume_bytes))
    if not resume_text:
        raise ValueError("Could not extract text from the provided resume PDF bytes.")

    # UPDATED prompt to be more direct and demand conciseness
    resume_scoring_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are an expert AI resume screener. Your task is to evaluate a resume against a job description with extreme conciseness to save tokens.
            
            **Output Rules:**
            - For all 'reason' and 'highlights' fields, you MUST provide a single, succinct sentence.
            - Do not speculate or add any information not directly supported by the resume.
            - Calculate a weighted aggregate score: Technical (50%), Experience & Alignment (30%), Soft Skills (20%).

            **Evaluation Criteria:**
            - **Strictness Level ({strictness_level}):** Apply this level of scrutiny.
            - **Positive Factors to reward:** {positive_factors}
            - **Negative Factors to penalize:** {negative_factors}
            
            Provide your assessment in the specified JSON format.
            """),
            ("human", """
            **Job Description:**
            {job_description}
            ---
            **Candidate Resume Text:**
            {resume_text}
            ---
            Evaluate the resume and provide the structured output, adhering strictly to the conciseness rules.
            """)
        ]
    )

    resume_scoring_chain = resume_scoring_prompt | llm.with_structured_output(ResumeScore)
    resume_score: ResumeScore = resume_scoring_chain.invoke({
        "strictness_level": strictness_level,
        "job_description": job_description_prompt,
        "resume_text": resume_text,
        "positive_factors": positive_factors or "No specific positive factors provided.",
        "negative_factors": negative_factors or "No specific negative factors provided.",
    })

    # Recalculate aggregate score to ensure consistency with the new weights
    weighted_score = (
        (resume_score.technical_score * 0.5) +
        (resume_score.experience_and_alignment_score * 0.3) +
        (resume_score.softskills_score * 0.2)
    )
    resume_score.aggregate_score = round(weighted_score, 2)
    return resume_score


def get_recommendations(candidate_scores: List[Dict[str, Any]], num_recommendations: int) -> RecommendationList:
    """ Unchanged from original """
    llm = get_llm()
    sorted_candidates = sorted([s for s in candidate_scores if 'aggregate_score' in s], key=lambda x: x['aggregate_score'], reverse=True)
    top_n_candidates = sorted_candidates[:num_recommendations]
    candidate_data_str = json.dumps(top_n_candidates, indent=2)
    recommendation_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an AI HR assistant. Based on the sorted list of candidates, provide exactly {num_recommendations} recommendations with concise reasons."),
            ("human", "Candidate Scores: {candidate_data}"),
        ]
    )
    recommendation_chain = recommendation_prompt | llm.with_structured_output(RecommendationList)
    recommendations: RecommendationList = recommendation_chain.invoke(
        {"candidate_data": candidate_data_str, "num_recommendations": num_recommendations}
    )
    return recommendations

# --- UPDATED MODULE FUNCTIONS for Conciseness ---

def detect_red_flags(resume_text: str) -> RedFlags:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an HR compliance AI. Analyze the resume for red flags (job hopping, gaps, buzzwords, inconsistencies). Provide a boolean `red_flags_found` and a concise, single-paragraph summary (max 80 words) of your findings."),
            ("human", "Resume Text: {resume_text}"),
        ]
    )
    chain = prompt | llm.with_structured_output(RedFlags)
    return chain.invoke({"resume_text": resume_text})

def estimate_salary(job_description: str, resume_text: str) -> SalaryEstimation:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a salary estimation AI. Based on the job and resume, provide an estimated annual salary range in India. Then, provide a concise, single-paragraph summary (max 80 words) justifying your estimate."),
            ("human", "Job Description: {job_description}\nResume Text: {resume_text}"),
        ]
    )
    chain = prompt | llm.with_structured_output(SalaryEstimation)
    return chain.invoke({"job_description": job_description, "resume_text": resume_text})

def check_background_consistency(resume_text: str) -> ConsistencyCheck:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an HR verification AI. Analyze the resume for inconsistencies in education, job titles, and dates. Provide a boolean `inconsistencies_found` and a concise, single-paragraph summary (max 80 words) of your findings."),
            ("human", "Resume Text: {resume_text}"),
        ]
    )
    chain = prompt | llm.with_structured_output(ConsistencyCheck)
    return chain.invoke({"resume_text": resume_text})

def calculate_fit_score(job_description: str, resume_text: str) -> FitScore:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a candidate fit AI. Provide a Role Fit score (0-10) and a Culture Fit score (0-10). Then, provide a concise, single-paragraph summary (max 80 words) explaining your overall assessment."),
            ("human", "Job Description: {job_description}\nResume Text: {resume_text}"),
        ]
    )
    chain = prompt | llm.with_structured_output(FitScore)
    return chain.invoke({"job_description": job_description, "resume_text": resume_text})