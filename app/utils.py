import os
import fitz  # PyMuPDF
import docx
import re
import spacy
from nltk.corpus import stopwords
import nltk
import logging
import time
import json
from functools import lru_cache

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure file handler if not already present
log_file = 'resume_ranking.log'
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, mode='w')
    logger.addHandler(file_handler)

# Custom JSON log formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage(),
            'file': record.filename,
            'line': record.lineno
        }
        return json.dumps(log_data)

# Apply formatter to all handlers
for handler in logger.handlers:
    handler.setFormatter(JsonFormatter())

# Download NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    logger.error(json.dumps({"event": "nltk_download_failed", "details": "Failed to download NLTK data"}))
    raise

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except:
    logger.error(json.dumps({"event": "spacy_load_failed", "details": "Failed to load spaCy model"}))
    raise

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
    logger.info(json.dumps({"event": "extract_text_start", "file_path": file_path}))
    start_time = time.time()
    try:
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > 10:
            logger.warning(json.dumps({"event": "file_too_large", "file_path": file_path, "size_mb": file_size}))
            return ""

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            text = ""
            with fitz.open(file_path) as doc:
                if doc.page_count > 50:
                    logger.warning(json.dumps({"event": "too_many_pages", "file_path": file_path, "page_count": doc.page_count}))
                    return ""
                for page in doc:
                    if time.time() - start_time > 20:
                        logger.error(json.dumps({"event": "extract_timeout", "file_path": file_path, "elapsed_time": time.time() - start_time}))
                        return ""
                    text += page.get_text()
            if not text.strip():
                logger.warning(json.dumps({"event": "no_text_extracted", "file_path": file_path}))
                return ""
            logger.info(json.dumps({"event": "extract_text_success", "file_path": file_path, "text_length": len(text), "elapsed_time": time.time() - start_time}))
            return text
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            if time.time() - start_time > 20:
                logger.error(json.dumps({"event": "extract_timeout", "file_path": file_path, "elapsed_time": time.time() - start_time}))
                return ""
            if not text.strip():
                logger.warning(json.dumps({"event": "no_text_extracted", "file_path": file_path}))
                return ""
            logger.info(json.dumps({"event": "extract_text_success", "file_path": file_path, "text_length": len(text), "elapsed_time": time.time() - start_time}))
            return text
        else:
            logger.error(json.dumps({"event": "unsupported_file", "file_path": file_path, "extension": ext}))
            raise ValueError(f"Unsupported file extension: {ext}")
    except Exception as e:
        logger.error(json.dumps({"event": "extract_text_error", "file_path": file_path, "error": str(e)}))
        return ""

@lru_cache(maxsize=10)
def read_job_description(file_path):
    """Read and cache job description from a text file."""
    logger.info(json.dumps({"event": "read_job_desc_start", "file_path": file_path}))
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read().strip()
        if not text.strip():
            logger.error(json.dumps({"event": "empty_job_desc", "file_path": file_path}))
            raise ValueError("Job description is empty")
        logger.info(json.dumps({"event": "read_job_desc_success", "file_path": file_path, "text_length": len(text)}))
        return text
    except Exception as e:
        logger.error(json.dumps({"event": "read_job_desc_error", "file_path": file_path, "error": str(e)}))
        raise

def clean_text(text, role=None):
    """Clean text using optimized spaCy pipe processing."""
    logger.info(json.dumps({"event": "clean_text_start", "role": role, "text_length": len(text) if text else 0}))
    start_time = time.time()
    if not text or not text.strip():
        logger.warning(json.dumps({"event": "empty_text", "role": role}))
        return ""
    try:
        text = text.lower()
        text = re.sub(r"https?://\S+|www\.\S+", "", text)
        text = re.sub(r"[^a-zA-Z\s\.\-]", "", text)
        text = text[:100000]
        
        role_keywords_set = set(ROLE_KEYWORDS.get(role.lower(), []))
        stop_words = set(stopwords.words("english"))
        tokens = []
        
        for doc in nlp.pipe([text], batch_size=1):
            if time.time() - start_time > 20:
                logger.error(json.dumps({"event": "clean_timeout", "role": role, "elapsed_time": time.time() - start_time}))
                return ""
            i = 0
            while i < len(doc):
                token = doc[i]
                if token.text in stop_words or len(token.text) <= 2:
                    i += 1
                    continue
                found_compound = False
                for j in range(1, 3):
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
            logger.warning(json.dumps({"event": "no_tokens", "role": role}))
            return ""

        if role:
            weighted_tokens = []
            for token in tokens:
                weight = 10 if token in role_keywords_set else 1
                weighted_tokens.extend([token] * weight)
            tokens = weighted_tokens

        cleaned_text = " ".join(tokens)
        logger.info(json.dumps({"event": "clean_text_success", "role": role, "text_length": len(cleaned_text), "elapsed_time": time.time() - start_time}))
        return cleaned_text
    except Exception as e:
        logger.error(json.dumps({"event": "clean_text_error", "role": role, "error": str(e)}))
        return ""