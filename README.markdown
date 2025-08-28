# Resume Ranking System

A professional tool to rank resumes based on their relevance to a job description using TF-IDF and cosine similarity. Built by **K. Mahesh Syam Kumar** for efficient resume screening, this system provides relative scores (0-10 scale), a Streamlit-based UI with visualizations, and supports PDF/DOCX resumes.

## Features
- **Relative Scoring**: Ranks resumes on a 0-10 scale based on similarity to the job description.
- **Role-Specific Keyword Weighting**: Boosts scores for resumes mentioning key skills (e.g., "Python", "SQL" for dataScience; "UI/UX", "React" for designer).
- **Streamlit UI**: Interactive interface with job role selection, job description display, resume uploads, ranked results, top 3 previews, visualizations (bar chart, histogram, top 3 comparison, keyword matches), and a "Clear Cache" button.
- **Supported Roles**: IT Officer, Teacher, Data Science (includes Data Analyst), Designer (includes Web Developer), Business Analyst.
- **Supported Formats**: Processes PDF and DOCX resumes.
- **Visual Insights**: Includes bar charts, histograms, and keyword match analysis for top resumes.
- **Performance Optimization**: Limits processing to 50 resumes, uses spaCy pipe for text cleaning, and caches job descriptions.
- **Robustness**: Handles duplicate resume names and provides detailed error messages.

## Directory Structure
```
E:\ResumeRanking\
├── app/
│   ├── __init__.py
│   ├── utils.py          # Text extraction and cleaning utilities
│   ├── scorer.py         # TF-IDF and scoring logic
│   └── interface.py      # Streamlit UI implementation
├── job_descriptions/
│   ├── itOfficer.txt     # IT Officer job description
│   ├── teacher.txt       # Teacher job description
│   ├── dataScience.txt   # Data Science and Data Analyst job description
│   ├── designer.txt      # Designer and Web Developer job description
│   ├── businessAnalyst.txt # Business Analyst job description
├── sample_data/
│   ├── cv_itOfficer/     # IT Officer resumes
│   ├── cv_teacher/       # Teacher resumes
│   ├── cv_dataScience/   # Data Science and Data Analyst resumes
│   ├── cv_designer/      # Designer and Web Developer resumes
│   ├── cv_businessAnalyst/ # Business Analyst resumes
├── main.py               # Entry point for Streamlit app
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Prerequisites
- **Python**: 3.8 or higher
- **Operating System**: Windows (tested on Windows 10/11)
- **Dependencies**: Listed in `requirements.txt`
- **Sample Resumes**: Place PDF/DOCX resumes in `sample_data/cv_<role>/` (e.g., `sample_data/cv_dataScience/` for Data Science/Data Analyst resumes)
- **Job Descriptions**: Ensure `.txt` files exist in `job_descriptions/` (e.g., `dataScience.txt`)

## Installation
1. **Set Up the Project**:
   - Ensure the project is in `E:\ResumeRanking\`.
   - If cloning from a repository:
     ```bash
     git clone <repository_url>
     cd E:\ResumeRanking
     ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   python -m nltk.downloader punkt stopwords
   ```

4. **Fix Matplotlib Font Cache (to resolve glyph warnings)**:
   ```bash
   python -c "import matplotlib.font_manager; matplotlib.font_manager._rebuild()"
   ```

## Usage
1. **Prepare Resumes**:
   - Place resumes in the appropriate folder (e.g., `sample_data/cv_dataScience/` for Data Science/Data Analyst resumes, `sample_data/cv_designer/` for Designer/Web Developer resumes).
   - Ensure resumes are text-based (not image-based PDFs). Convert using Adobe Acrobat or [https://www.ilovepdf.com/](https://www.ilovepdf.com/).

2. **Run the Application**:
   ```bash
   streamlit run main.py
   ```

3. **Access the UI**:
   - Open `http://localhost:8501` in your browser.
   - Select a job role (e.g., "dataScience") from the sidebar dropdown.
   - Verify the job description loads (e.g., `job_descriptions/dataScience.txt`).
   - Upload resumes or use existing ones in `sample_data/cv_<role>/`.
   - View the number of resumes detected (uploaded + sample).
   - Click "Clear Cache" to remove temporary files if needed.
   - Click "Rank Resumes" to view:
     - Ranked table with `Name` and `RelativeScore` (0-10).
     - Top 3 resumes with 500-character previews.
     - Visualizations: Bar chart, histogram, top 3 comparison, and top resume keyword matches.
   - Download results as `resume_ranking_results.csv`.


## Expected Output
For Data Science/Data Analyst resumes (e.g., two uploaded files):
| Name         | RelativeScore |
|--------------|---------------|
| resume1.pdf  | 9.50          |
| resume2.docx | 8.20          |

## Notes
- **Data Science Role**: The `cv_dataScience` folder includes Data Science and Data Analyst resumes, scored against `dataScience.txt`.
- **Designer Role**: The `cv_designer` folder includes Designer and Web Developer resumes, scored against `designer.txt`.
- **Performance**: Limits to 50 resumes by default. Adjust `max_resumes` in `scorer.py` for larger datasets.
- **Logging**: JSON logs in `resume_ranking.log` provide detailed debugging info.
- **Resume Quality**: Resumes should mention role-specific skills for accurate scoring.

## Author
**K. Mahesh Syam Kumar**  
Built for efficient resume screening and showcased for placement purposes.