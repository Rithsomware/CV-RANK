from flask import Flask, request, render_template
import os
import docx2txt
import PyPDF2
import spacy

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Load spaCy's pre-trained language model
nlp = spacy.load('en_core_web_md')  # Use 'en_core_web_lg' for better accuracy

# Domain-specific keyword lists
DOMAIN_KEYWORDS = {
    "Senior WordPress Developer": ["wordpress", "php", "mysql", "html5", "css3", "javascript", "git", "seo"],
    "Graphic Designer": ["adobe photoshop", "illustrator", "figma", "canva", "web design", "adobe xd"],
    "Cinematographer": ["adobe premiere pro", "adobe photoshop", "video editing", "photography", "cinematography"],
    "Financial Sales Officer": ["sales", "finance", "customer service", "business development", "banking"],
    "Associate Content Writer": ["content writing", "seo", "blogging", "creative writing", "social media marketing"]
}

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

def calculate_keyword_score(resume_text, domain_keywords):
    """
    Calculate a keyword-based score based on the presence of domain-specific keywords.
    """
    if not domain_keywords:  # Check if the keyword list is empty
        return 0.0  # Return a score of 0 if no keywords are defined

    resume_text_lower = resume_text.lower()
    keyword_count = sum(1 for keyword in domain_keywords if keyword in resume_text_lower)
    return keyword_count / len(domain_keywords)  # Normalize to 0-1

@app.route("/")
def matchresume():
    return render_template('matchresume.html')

@app.route('/matcher', methods=['POST'])
def matcher():
    if request.method == 'POST':
        # Get uploaded job description files
        job_description_files = request.files.getlist('job_descriptions')
        # Get uploaded resume files
        resume_files = request.files.getlist('resumes')

        if not job_description_files or not resume_files:
            return render_template('matchresume.html', message="Please upload both job descriptions and resumes.")

        # Extract text from job description files
        job_descriptions = []
        for job_file in job_description_files:
            if job_file.filename == '':
                continue
            filename = os.path.join(app.config['UPLOAD_FOLDER'], job_file.filename)
            job_file.save(filename)
            text = extract_text(filename)
            if text:
                job_descriptions.append((job_file.filename, text))
            os.remove(filename)  # Clean up uploaded file

        # Extract text from resume files
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

        if not job_descriptions or not resumes:
            return render_template('matchresume.html', message="No valid job descriptions or resumes found.")

        # Process each job description and rank resumes
        results = []
        for job_desc in job_descriptions:
            job_doc = nlp(job_desc[1])  # Process job description with spaCy
            job_title = job_desc[0].replace(".txt", "").replace(".docx", "").replace(".pdf", "")
            domain_keywords = DOMAIN_KEYWORDS.get(job_title, [])

            combined_scores = []
            for resume in resumes:
                resume_doc = nlp(resume[1])  # Process resume with spaCy
                similarity = job_doc.similarity(resume_doc)  # spaCy's similarity score (0 to 1)
                keyword_score = calculate_keyword_score(resume[1], domain_keywords)  # Keyword-based score (0 to 1)
                combined_score = 0.7 * similarity + 0.3 * keyword_score  # Weighted score
                combined_score_percent = combined_score * 100  # Convert to percentage
                combined_scores.append((resume[0], combined_score_percent))

            # Sort resumes by combined score (descending order)
            combined_scores.sort(key=lambda x: x[1], reverse=True)
            results.append({
                'job_description': job_title,
                'ranked_resumes': combined_scores
            })

        return render_template('matchresume.html', results=results)

    return render_template('matchresume.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)