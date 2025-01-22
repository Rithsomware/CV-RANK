from flask import Flask, request, render_template
import os
import docx2txt
import PyPDF2
import spacy

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Load spaCy's pre-trained language model
nlp = spacy.load('en_core_web_md')  # Use 'en_core_web_lg' for better accuracy

# Define required keywords for the job description
REQUIRED_KEYWORDS = ["wordpress", "php", "html5", "css3", "javascript", "mysql", "git", "seo"]

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        print(f"Error reading DOCX file: {e}")
        return ""

def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading TXT file: {e}")
        return ""

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.txt'):
        return extract_text_from_txt(file_path)
    else:
        return ""

def calculate_keyword_score(resume_text):
    """
    Calculate a keyword-based score based on the presence of required keywords.
    """
    resume_text_lower = resume_text.lower()
    keyword_count = sum(1 for keyword in REQUIRED_KEYWORDS if keyword in resume_text_lower)
    return keyword_count / len(REQUIRED_KEYWORDS)  # Normalize to 0-1

@app.route("/")
def matchresume():
    return render_template('matchresume.html')

@app.route('/matcher', methods=['POST'])
def matcher():
    if request.method == 'POST':
        job_description = request.form['job_description']
        resume_files = request.files.getlist('resumes')

        if not resume_files or not job_description:
            return render_template('matchresume.html', message="Please upload resumes and enter a job description.")

        resumes = []
        for resume_file in resume_files:
            if resume_file.filename == '':
                continue
            filename = os.path.join(app.config['UPLOAD_FOLDER'], resume_file.filename)
            resume_file.save(filename)
            text = extract_text(filename)
            if text:
                resumes.append((resume_file.filename, text))
            os.remove(filename)  # Clean up uploaded file

        if not resumes:
            return render_template('matchresume.html', message="No valid resumes found.")

        # Process the job description with spaCy
        job_doc = nlp(job_description)

        # Calculate combined scores (semantic similarity + keyword score)
        combined_scores = []
        for resume in resumes:
            resume_doc = nlp(resume[1])
            similarity = job_doc.similarity(resume_doc)  # spaCy's similarity score (0 to 1)
            keyword_score = calculate_keyword_score(resume[1])  # Keyword-based score (0 to 1)
            combined_score = 0.7 * similarity + 0.3 * keyword_score  # Weighted score
            combined_scores.append((resume[0], combined_score))

        # Sort resumes by combined score (descending order)
        combined_scores.sort(key=lambda x: x[1], reverse=True)

        # Get top resumes and their similarity scores
        top_resumes = [resume[0] for resume in combined_scores]
        similarity_scores = [round(resume[1], 2) for resume in combined_scores]

        return render_template('matchresume.html', message="Top matching resumes:", top_resumes=top_resumes, similarity_scores=similarity_scores)

    return render_template('matchresume.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)