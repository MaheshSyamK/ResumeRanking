import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from app.scorer import compute_scores
from app.utils import extract_text, ROLE_KEYWORDS, logger
import shutil
import json
from collections import Counter
import re
import matplotlib

# Set Matplotlib font to avoid glyph warnings
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

def plot_relative_scores(df):
    """Bar chart of resume scores."""
    logger.info(json.dumps({"event": "plot_relative_scores_start"}))
    fig, ax = plt.subplots(figsize=(12, min(len(df)*0.4, 20)))
    sns.barplot(x='RelativeScore', y='Name', hue='Name', data=df, ax=ax, palette='Blues_d', legend=False)
    ax.set_xlabel("Relative Score (0-10)")
    ax.set_title("Resume Ranking by Similarity Score")
    plt.tight_layout()
    st.pyplot(fig)
    logger.info(json.dumps({"event": "plot_relative_scores_success"}))

def plot_score_distribution(df):
    """Histogram of score distribution."""
    logger.info(json.dumps({"event": "plot_score_distribution_start"}))
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(df['RelativeScore'], bins=10, kde=True, ax=ax, color='skyblue')
    ax.set_xlabel("Relative Score (0-10)")
    ax.set_title("Score Distribution")
    plt.tight_layout()
    st.pyplot(fig)
    logger.info(json.dumps({"event": "plot_score_distribution_success"}))

def plot_top3_comparison(df):
    """Bar chart comparing top 3 resumes."""
    logger.info(json.dumps({"event": "plot_top3_comparison_start"}))
    top3 = df.head(3)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(x='RelativeScore', y='Name', hue='Name', data=top3, ax=ax, palette='viridis', legend=False)
    ax.set_xlabel("Relative Score (0-10)")
    ax.set_title("Top 3 Resumes Comparison")
    plt.tight_layout()
    st.pyplot(fig)
    logger.info(json.dumps({"event": "plot_top3_comparison_success"}))

def plot_keyword_matches(df, resume_dir, role):
    """Bar chart of top 5 keyword matches for top resume."""
    logger.info(json.dumps({"event": "plot_keyword_matches_start", "role": role}))
    if not df.empty:
        top_resume = df.iloc[0]['Name']
        resume_path = os.path.join(resume_dir, top_resume)
        try:
            text = extract_text(resume_path).lower()
            keywords = ROLE_KEYWORDS.get(role.lower(), [])
            matches = Counter([kw for kw in keywords if re.search(rf'\b{re.escape(kw)}\b', text)])
            if matches:
                top_keywords = dict(matches.most_common(5))
                fig, ax = plt.subplots(figsize=(8, 4))
                sns.barplot(x=list(top_keywords.values()), y=list(top_keywords.keys()), hue=list(top_keywords.keys()), palette='magma', legend=False)
                ax.set_xlabel("Match Count")
                ax.set_title(f"Top 5 Keyword Matches in {top_resume}")
                plt.tight_layout()
                st.pyplot(fig)
                logger.info(json.dumps({"event": "plot_keyword_matches_success", "top_resume": top_resume}))
            else:
                st.write("No keyword matches found in top resume.")
                logger.info(json.dumps({"event": "no_keyword_matches", "top_resume": top_resume}))
        except Exception as e:
            st.error(f"Error analyzing keywords for {top_resume}: {str(e)}")
            logger.error(json.dumps({"event": "plot_keyword_matches_error", "top_resume": top_resume, "error": str(e)}))

def resume_interface():
    """Streamlit interface for resume ranking."""
    st.set_page_config(page_title="Resume Ranker", layout="wide", initial_sidebar_state="expanded")
    st.title("Professional Resume Ranker")
    st.markdown("""
    Welcome to the Resume Ranker! Select a job role, upload resumes, and get ranked results (0-10 scale) with visualizations.
    Built by **K. Mahesh Syam Kumar** for efficient resume screening.
    """)

    # Sidebar for job role selection
    with st.sidebar:
        st.header("Job Role Selection")
        job_roles = sorted([f.replace('.txt', '') for f in os.listdir("job_descriptions") if f.endswith('.txt')])
        if not job_roles:
            st.error("No job description files found in 'job_descriptions/'.")
            logger.error(json.dumps({"event": "no_job_roles", "directory": "job_descriptions"}))
            return
        selected_role = st.selectbox("Select Job Role", job_roles, help="Choose a role to load its description.")
        
        # Load and display job description
        job_desc_path = os.path.join("job_descriptions", f"{selected_role}.txt")
        try:
            job_desc = open(job_desc_path, 'r', encoding='utf-8').read()
            st.subheader(f"{selected_role.title()} Job Description")
            st.text_area("Description", value=job_desc, height=300, disabled=True, help="Auto-loaded job description.")
        except Exception as e:
            st.error(f"Error loading job description: {str(e)}")
            logger.error(json.dumps({"event": "load_job_desc_error", "file_path": job_desc_path, "error": str(e)}))
            return

        # Clear cache button
        if st.button("Clear Cache", help="Remove temporary resume files"):
            temp_dir = "temp_resumes_combined"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                st.success("Temporary resume cache cleared.")
                logger.info(json.dumps({"event": "clear_cache_success", "directory": temp_dir}))

    # Main content
    st.header(f"Ranking Resumes for {selected_role.title()}")
    sample_resume_dir = f"sample_data/cv_{selected_role}/"
    uploaded_files = st.file_uploader(
        f"Upload {selected_role.title()} Resumes (PDF/DOCX)",
        accept_multiple_files=True,
        type=['pdf', 'docx'],
        help=f"These will be ranked alongside resumes from {sample_resume_dir}."
    )

    # Display file counts
    sample_files = [f for f in os.listdir(sample_resume_dir) if f.endswith(('.pdf', '.docx'))] if os.path.exists(sample_resume_dir) else []
    st.info(f"Found {len(sample_files)} resumes in {sample_resume_dir} and {len(uploaded_files)} uploaded resumes.")

    if st.button("Rank Resumes", type="primary"):
        temp_dir = "temp_resumes_combined"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        # Save uploaded files with duplicate name handling
        uploaded_names = set()
        failed_files = []
        if uploaded_files:
            progress_bar = st.progress(0)
            for i, file in enumerate(uploaded_files):
                base, ext = os.path.splitext(file.name)
                counter = 1
                new_name = file.name
                while new_name in uploaded_names:
                    new_name = f"{base}_{counter}{ext}"
                    counter += 1
                uploaded_names.add(new_name)
                try:
                    with open(os.path.join(temp_dir, new_name), "wb") as f:
                        f.write(file.getvalue())
                except Exception as e:
                    failed_files.append(file.name)
                    logger.error(json.dumps({"event": "save_uploaded_file_error", "filename": file.name, "error": str(e)}))
                progress_bar.progress((i + 1) / len(uploaded_files))
            progress_bar.empty()

        # Copy sample files, skipping duplicates
        if os.path.exists(sample_resume_dir):
            for filename in os.listdir(sample_resume_dir):
                if filename.endswith(('.pdf', '.docx')):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    new_name = filename
                    while new_name in uploaded_names:
                        new_name = f"{base}_{counter}{ext}"
                        counter += 1
                    uploaded_names.add(new_name)
                    shutil.copy(os.path.join(sample_resume_dir, filename), os.path.join(temp_dir, new_name))

        resumes_in_dir = [f for f in os.listdir(temp_dir) if f.endswith(('.pdf', '.docx'))]
        if not resumes_in_dir:
            st.error(f"No resumes found to rank. Upload files or add them to '{sample_resume_dir}'.")
            logger.error(json.dumps({"event": "no_resumes", "directory": temp_dir}))
            return

        try:
            with st.spinner(f"Ranking {len(resumes_in_dir)} resumes..."):
                df = compute_scores(temp_dir, job_desc_path, role=selected_role)
            
            st.success(f"Scored {len(df)} resumes for {selected_role.title()}")
            if df['RelativeScore'].max() < 4:
                st.warning(f"Low scores detected. Ensure resumes mention relevant skills (e.g., '{', '.join(ROLE_KEYWORDS.get(selected_role.lower(), [])[:3])}'). Check resume_ranking.log.")
                logger.warning(json.dumps({"event": "low_scores", "max_score": float(df['RelativeScore'].max())}))

            st.subheader("Ranked Resumes")
            st.dataframe(df, use_container_width=True)

            top3 = df.head(3)
            st.subheader("Top 3 Resumes")
            for i, row in top3.iterrows():
                with st.expander(f"{i+1}. {row['Name']} — {row['RelativeScore']}/10"):
                    try:
                        resume_path = os.path.join(temp_dir, row['Name'])
                        text = extract_text(resume_path)[:500]
                        st.text_area(f"Preview of {row['Name']}", text, height=150, disabled=True)
                    except Exception as e:
                        st.error(f"Error previewing {row['Name']}: {str(e)}")
                        logger.error(json.dumps({"event": "preview_error", "filename": row['Name'], "error": str(e)}))

            st.subheader("Visual Insights")
            with st.expander("View Graphs", expanded=True):
                st.write("Resume Ranking Bar Chart")
                plot_relative_scores(df)
                st.write("Score Distribution Histogram")
                plot_score_distribution(df)
                st.write("Top 3 Resumes Comparison")
                plot_top3_comparison(df)
                st.write("Top Resume Keyword Matches")
                plot_keyword_matches(df, temp_dir, selected_role)

            st.download_button(
                label="Download Results",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="resume_ranking_results.csv",
                mime="text/csv",
                help="Download the ranked results as a CSV file."
            )

        except Exception as e:
            st.error(f"An error occurred during ranking: {str(e)}")
            logger.error(json.dumps({"event": "ranking_error", "error": str(e)}))
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(json.dumps({"event": "cleanup_temp_dir", "directory": temp_dir}))