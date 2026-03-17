

"""Resume Parser - Extract text from PDF and DOCX"""
import PyPDF2
from docx import Document
import re
from typing import List

class ResumeParser:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        except Exception as e:
            print(f"Error reading PDF: {e}")
        return text
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX file"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error reading DOCX: {e}")
        return text
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Auto-detect and extract text"""
        if file_path.lower().endswith('.pdf'):
            return ResumeParser.extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return ResumeParser.extract_text_from_docx(file_path)
        else:
            raise ValueError("Unsupported file format. Use PDF or DOCX.")
    
    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract skills using keyword matching"""
        common_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue',
            'node', 'django', 'flask', 'fastapi', 'sql', 'postgresql',
            'mongodb', 'aws', 'azure', 'docker', 'kubernetes', 'git',
            'machine learning', 'data science', 'nlp', 'deep learning',
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
            'html', 'css', 'bootstrap', 'tailwind', 'c++', 'c#', 'golang',
            'rust', 'typescript', 'php', 'laravel', 'spring', 'hibernate'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates

