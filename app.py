import os
import json
import streamlit as st
from pypdf import PdfReader
from docx import Document
from google import genai

st.set_page_config(
page_title="Resume ATS Analyzer",
page_icon="📄",
layout="wide"
)

st.markdown("""

<style>
.main-title {
    font-size: 38px;
    font-weight: bold;
    text-align: center;
    color: #2563eb;
}
.subtitle {
    text-align: center;
    font-size: 17px;
    color: #64748b;
}
div[data-testid="stMetric"] {
    background-color: #f1f5f9;
    padding: 18px;
    border-radius: 12px;
}
</style>""", unsafe_allow_html=True)

st.markdown(
'<div class="main-title">📄 Resume ATS Analyzer</div>',
unsafe_allow_html=True
)

st.markdown(
'<div class="subtitle">Analyze your resume, estimate your ATS score, and discover ways to improve it with AI.</div>',
unsafe_allow_html=True
)

st.write("")

def get_api_key():
try:
key = st.secrets.get("GEMINI_API_KEY", "")
if key:
return key
except Exception:
pass

return os.getenv("GEMINI_API_KEY", "")

def extract_resume_text(uploaded_file):
filename = uploaded_file.name.lower()

if filename.endswith(".pdf"):
    reader = PdfReader(uploaded_file)

    if reader.is_encrypted:
        raise ValueError(
            "This PDF is password-protected. Upload an unlocked PDF."
        )

    text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

elif filename.endswith(".docx"):
    document = Document(uploaded_file)

    parts = [
        paragraph.text
        for paragraph in document.paragraphs
    ]

    for table in document.tables:
        for row in table.rows:
            parts.append(
                " | ".join(cell.text for cell in row.cells)
            )

    text = "\n".join(parts)

elif filename.endswith(".txt"):
    text = uploaded_file.getvalue().decode(
        "utf-8-sig",
        errors="replace"
    )

else:
    raise ValueError(
        "Unsupported file format. Upload PDF, DOCX, or TXT."
    )

text = text.strip()

if not text:
    raise ValueError(
        "No readable text found. Scanned PDFs may require OCR."
    )

if len(text) > 100000:
    raise ValueError("Resume is too long. Please upload a shorter file.")

return text

def analyze_resume(resume_text, job_description, api_key):
client = genai.Client(api_key=api_key)

job_text = job_description.strip() or (
    "No job description provided. Evaluate general ATS readiness."
)

prompt = f"""

You are an expert resume reviewer and ATS optimization assistant.

Analyze the resume against the supplied job description.

Rules:

1. Return only valid JSON.
2. Never invent qualifications, skills, degrees, or work experience.
3. Give an estimated ATS readiness score from 0 to 100.
4. Explain that this score is an estimate, not a score from a real ATS.
5. Identify strengths, weaknesses, missing keywords, formatting issues,
   and actionable improvements.
6. If no job description is provided, assess general resume readiness.
7. Keep recommendations practical and specific.

Use this JSON structure:
{{
"ats_score": 70,
"summary": "Short assessment",
"strengths": ["Strength 1", "Strength 2"],
"weaknesses": ["Weakness 1", "Weakness 2"],
"missing_keywords": ["Keyword 1", "Keyword 2"],
"formatting_issues": ["Issue 1"],
"improvements": ["Improvement 1", "Improvement 2"],
"suggested_summary": "A truthful improved professional summary",
"keyword_match": "Explanation of job keyword alignment"
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_text}
"""

response = client.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    contents=prompt,
    config={
        "response_mime_type": "application/json"
    }
)

result_text = response.text

if not result_text:
    raise ValueError("The AI returned an empty response. Try again.")

result = json.loads(result_text)

if not isinstance(result, dict):
    raise ValueError("The AI returned an invalid response.")

score = result.get("ats_score")

if not isinstance(score, (int, float)) or isinstance(score, bool):
    raise ValueError("The AI returned an invalid ATS score.")

result["ats_score"] = max(0, min(100, round(score)))

return result

st.subheader("📤 Upload Your Resume")

uploaded_file = st.file_uploader(
"Choose your resume",
type=["pdf", "docx", "txt"],
help="Supported formats: PDF, DOCX and TXT"
)

st.subheader("💼 Job Description")

job_description = st.text_area(
"Paste the job description here (optional)",
height=180,
placeholder="Paste the job requirements to get a more relevant ATS analysis."
)

st.info(
"Your ATS score is an AI-generated estimate. Different employers "
"and ATS platforms may evaluate resumes differently."
)

if st.button("🔍 Analyze My Resume", type="primary", use_container_width=True):

if uploaded_file is None:
    st.error("Please upload your resume first.")

else:
    api_key = get_api_key()

    if not api_key:
        st.error(
            "Gemini API key is missing. Add GEMINI_API_KEY "
            "in Streamlit Secrets or your environment variables."
        )

    else:
        try:
            with st.spinner("Reading and analyzing your resume..."):
                resume_text = extract_resume_text(uploaded_file)

                result = analyze_resume(
                    resume_text,
                    job_description,
                    api_key
                )

            st.success("Resume analysis completed!")

            st.subheader("📊 Your ATS Results")

            score = result["ats_score"]

            col1, col2 = st.columns([1, 2])

            with col1:
                st.metric("Estimated ATS Score", f"{score}/100")
                st.progress(score / 100)

            with col2:
                st.markdown("### Overall Assessment")
                st.write(result.get("summary", "No summary provided."))

            sections = [
                ("✅ Strengths", "strengths"),
                ("⚠️ Weaknesses", "weaknesses"),
                ("🔑 Missing Keywords", "missing_keywords"),
                ("📝 Formatting Issues", "formatting_issues"),
                ("🚀 Recommended Improvements", "improvements")
            ]

            for heading, key in sections:
                st.subheader(heading)
                items = result.get(key, [])

                if isinstance(items, list) and items:
                    for item in items:
                        st.markdown(f"- {item}")
                else:
                    st.write("No specific items returned.")

            st.subheader("🎯 Job Keyword Alignment")
            st.write(
                result.get(
                    "keyword_match",
                    "No keyword alignment explanation provided."
                )
            )

            st.subheader("✍️ Suggested Professional Summary")
            st.write(
                result.get(
                    "suggested_summary",
                    "No suggested summary provided."
                )
            )

            report = json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )

            st.download_button(
                label="⬇️ Download Analysis Report",
                data=report,
                file_name="resume_ats_analysis.json",
                mime="application/json",
                use_container_width=True
            )

        except json.JSONDecodeError:
            st.error(
                "The AI returned an invalid report format. Please try again."
            )

        except Exception as error:
            st.error(
                "Analysis failed. Check your Gemini API key, "
                "model availability, internet connection, and logs."
            )
            st.caption(f"Technical details: {str(error)[:500]}")
