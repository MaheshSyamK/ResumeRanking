import os
import fitz  # PyMuPDF
import docx
import re
import spacy
from nltk.corpus import stopwords
import nltk
import time
from functools import lru_cache

# Download NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    raise RuntimeError("Failed to download NLTK data")

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except:
    raise RuntimeError("Failed to load spaCy model")

# Role-specific keywords for weighting
ROLE_KEYWORDS = {
    "itOfficer": ["network", "security", "cloud", "linux", "windows", "virtualization", "sql", "python", "bash", "powershell", "itil", "devops", "troubleshooting", "aws", "azure", "gcp", "vmware", "docker", "cybersecurity", "database"],
    "teacher": ["curriculum", "pedagogy", "classroom", "education", "lesson", "assessment", "mathematics", "science", "literature", "educational technology", "smartboard", "moodle", "teaching", "student"],
    "dataScience": ["python", "r", "sql", "machine learning", "deep learning", "tableau", "powerbi", "excel", "hadoop", "spark", "statistics", "visualization", "etl", "predictive modeling", "data analysis", "business intelligence", "dashboard", "reporting"],
    "designer": ["ui/ux", "graphic design", "figma", "adobe xd", "photoshop", "html", "css", "javascript", "react", "angular", "vue.js", "nodejs", "django", "php", "seo", "api", "restful", "git", "aws", "heroku", "wireframing", "prototyping"],
    "businessAnalyst": ["requirements", "swot", "excel", "sql", "tableau", "powerbi", "business intelligence", "agile", "scrum", "project management", "financial analysis", "process modeling"]
}

def extract_text(file_path):
    """Extract text from PDF or DOCX files with manual timeout."""
    start_time = time.time()
    try:
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > 10:  # Skip very large files
            return ""

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            text = ""
            with fitz.open(file_path) as doc:
                if doc.page_count > 5:  
                    return ""
                for page in doc:
                    if time.time() - start_time > 20: 
                        return ""
                    text += page.get_text()
            return text if text.strip() else ""
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            if time.time() - start_time > 20:
                return ""
            return text if text.strip() else ""
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
    except Exception:
        return ""

@lru_cache(maxsize=10)
def read_job_description(file_path):
    """Read and cache job description from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read().strip()
        if not text.strip():
            raise ValueError("Job description is empty")
        return text
    except Exception:
        raise

def clean_text(text, role=None):
    """Clean text using optimized spaCy pipe processing with role keyword weighting."""
    start_time = time.time()
    if not text or not text.strip():
        return ""
    try:
        text = text.lower()
        text = re.sub(r"https?://\S+|www\.\S+", "", text)  # Remove URLs
        text = re.sub(r"[^a-zA-Z\s\.\-]", "", text)  # Keep only letters, space, dot, hyphen
        text = text[:100000]  # Limit size
        
        role_keywords_set = set(ROLE_KEYWORDS.get(role.lower(), [])) if role else set()
        stop_words = set(stopwords.words("english"))
        tokens = []
        
        for doc in nlp.pipe([text], batch_size=1):
            if time.time() - start_time > 20:
                return ""
            i = 0
            while i < len(doc):
                token = doc[i]
                if token.text in stop_words or len(token.text) <= 2:
                    i += 1
                    continue
                found_compound = False
                for j in range(1, 3):  # Try to capture bigrams/trigrams from ROLE_KEYWORDS
                    if i + j < len(doc):
                        compound = " ".join([doc[i+k].text for k in range(j + 1)])
                        if compound in role_keywords_set:
                            tokens.append(compound)
                            i += j + 1
                            found_compound = True
                            break
                if not found_compound:
                    tokens.append(token.text)
                    i += 1

        if not tokens:
            return ""

        if role:
            weighted_tokens = []
            for token in tokens:
                weight = 10 if token in role_keywords_set else 1
                weighted_tokens.extend([token] * weight)
            tokens = weighted_tokens

        return " ".join(tokens)
    except Exception:
        return ""
