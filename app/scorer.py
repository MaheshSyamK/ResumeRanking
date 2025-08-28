import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.utils import extract_text, clean_text, read_job_description
import numpy as np
import time

def compute_tfidf_scores(job_desc_clean, resumes, names):
    """Compute TF-IDF and similarity scores with manual timeout."""
    start_time = time.time()
    vectorizer = TfidfVectorizer(
        stop_words='english',
        min_df=1,
        max_df=0.95,
        ngram_range=(1, 3),
        max_features=1500
    )
    tfidf_matrix = vectorizer.fit_transform([job_desc_clean] + resumes)
    
    # Timeout check
    if time.time() - start_time > 30:
        raise TimeoutError("TF-IDF computation exceeded 30 seconds")

    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    return similarities

def compute_scores(resume_dir, job_desc_file, role, max_resumes=50):
    """Compute TF-IDF similarity scores (0-10) between job description and resumes."""
    # Read job description
    job_desc = read_job_description(job_desc_file)
    job_desc_clean = clean_text(job_desc, role=role)
    if not job_desc_clean:
        raise ValueError("Cleaned job description is empty")

    # Process resumes
    resumes = []
    names = []
    resume_files = [f for f in os.listdir(resume_dir) if f.endswith(('.pdf', '.docx'))][:max_resumes]
    
    for filename in resume_files:
        path = os.path.join(resume_dir, filename)
        try:
            file_size = os.path.getsize(path) / (1024 * 1024)
            if file_size > 10:  # skip if file >10MB
                continue
            raw = extract_text(path)
            if not raw:
                continue
            clean = clean_text(raw, role=role)
            if not clean:
                continue
            resumes.append(clean)
            names.append(filename)
        except Exception:
            continue

    if not resumes:
        raise ValueError("No valid resumes found after processing")

    # Compute TF-IDF and similarity
    similarities = compute_tfidf_scores(job_desc_clean, resumes, names)

    # Normalize scores to 0-10 scale
    max_similarity = similarities.max() if similarities.max() > 0 else 1
    normalized_scores = (similarities / max_similarity * 10).round(2)

    # Create DataFrame
    df = pd.DataFrame({
        'Name': names,
        'RelativeScore': normalized_scores
    })

    # Sort and save results
    df = df.sort_values(by='RelativeScore', ascending=False).reset_index(drop=True)
    os.makedirs("results", exist_ok=True)
    df.to_csv("results/output.csv", index=False)
    
    return df
