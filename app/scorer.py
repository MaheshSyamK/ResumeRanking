import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.utils import extract_text, clean_text, read_job_description, logger
import numpy as np
import time
import json

def compute_tfidf_scores(job_desc_clean, resumes, names):
    """Compute TF-IDF and similarity scores with manual timeout."""
    logger.info(json.dumps({"event": "compute_tfidf_start", "num_resumes": len(resumes)}))
    start_time = time.time()
    try:
        vectorizer = TfidfVectorizer(stop_words='english', min_df=1, max_df=0.95, ngram_range=(1, 3), max_features=1500)
        tfidf_matrix = vectorizer.fit_transform([job_desc_clean] + resumes)
        if time.time() - start_time > 30:
            logger.error(json.dumps({"event": "tfidf_timeout", "elapsed_time": time.time() - start_time}))
            raise TimeoutError("TF-IDF computation exceeded 30 seconds")
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        logger.info(json.dumps({"event": "compute_tfidf_success", "elapsed_time": time.time() - start_time}))
        return similarities
    except Exception as e:
        logger.error(json.dumps({"event": "compute_tfidf_error", "error": str(e)}))
        raise

def compute_scores(resume_dir, job_desc_file, role, max_resumes=50):
    """Compute TF-IDF similarity scores (0-10) between job description and resumes."""
    logger.info(json.dumps({"event": "compute_scores_start", "resume_dir": resume_dir, "role": role, "max_resumes": max_resumes}))
    try:
        # Read job description
        job_desc = read_job_description(job_desc_file)
        job_desc_clean = clean_text(job_desc, role=role)
        if not job_desc_clean:
            logger.error(json.dumps({"event": "empty_job_desc_clean", "job_desc_file": job_desc_file}))
            raise ValueError("Cleaned job description is empty")

        # Process resumes
        resumes = []
        names = []
        resume_files = [f for f in os.listdir(resume_dir) if f.endswith(('.pdf', '.docx'))][:max_resumes]
        logger.info(json.dumps({"event": "resume_files_listed", "num_files": len(resume_files)}))
        
        for i, filename in enumerate(resume_files):
            path = os.path.join(resume_dir, filename)
            logger.info(json.dumps({"event": "process_resume_start", "filename": filename, "index": i+1, "total": len(resume_files)}))
            try:
                file_size = os.path.getsize(path) / (1024 * 1024)
                if file_size > 10:
                    logger.warning(json.dumps({"event": "file_too_large", "filename": filename, "size_mb": file_size}))
                    continue
                raw = extract_text(path)
                if not raw:
                    logger.warning(json.dumps({"event": "no_text_extracted", "filename": filename}))
                    continue
                clean = clean_text(raw, role=role)
                if not clean:
                    logger.warning(json.dumps({"event": "empty_clean_text", "filename": filename}))
                    continue
                resumes.append(clean)
                names.append(filename)
                logger.info(json.dumps({"event": "process_resume_success", "filename": filename, "text_length": len(clean)}))
            except Exception as e:
                logger.error(json.dumps({"event": "process_resume_error", "filename": filename, "error": str(e)}))
                continue

        if not resumes:
            logger.error(json.dumps({"event": "no_valid_resumes", "resume_dir": resume_dir}))
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
        logger.info(json.dumps({"event": "save_results_success", "num_resumes": len(df), "output_file": "results/output.csv"}))
        return df
    except Exception as e:
        logger.error(json.dumps({"event": "compute_scores_error", "error": str(e)}))
        raise