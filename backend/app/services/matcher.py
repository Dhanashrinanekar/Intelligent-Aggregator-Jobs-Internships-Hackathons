
"""Cosine Similarity Matching Service"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from app.models import User, Opportunity, ResumeVector, JobVector, SimilarityScore
from app.services.vectorizer import VectorizerService
from typing import List, Dict
import json

class MatcherService:
    def __init__(self, db: Session):
        self.db = db
        self.vectorizer = VectorizerService()
    
    def calculate_similarity(self, resume_vector: np.ndarray, job_vector: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        similarity = cosine_similarity([resume_vector], [job_vector])[0][0]
        return float(similarity)
    
    def match_user_with_jobs(self, user_id: int, threshold: float = 0.75) -> List[Dict]:
        """Match user resume with all jobs"""
        # Get user's resume vector
        resume_vec = self.db.query(ResumeVector).filter(
            ResumeVector.user_id == user_id
        ).first()
        
        if not resume_vec:
            return []
        
        resume_array = np.array(json.loads(resume_vec.vector_data))
        
        # Get all job vectors
        job_vectors = self.db.query(JobVector).all()
        
        matches = []
        for jv in job_vectors:
            job_array = np.array(json.loads(jv.vector_data))
            score = self.calculate_similarity(resume_array, job_array)
            
            if score >= threshold:
                # Save to similarity_score table
                existing = self.db.query(SimilarityScore).filter(
                    SimilarityScore.user_id == user_id,
                    SimilarityScore.job_id == jv.job_id
                ).first()
                
                if existing:
                    existing.similarity_score = score
                    existing.email_sent = False  # Reset if score changed
                else:
                    new_score = SimilarityScore(
                        user_id=user_id,
                        job_id=jv.job_id,
                        similarity_score=score,
                        email_sent=False
                    )
                    self.db.add(new_score)
                
                matches.append({
                    'job_id': jv.job_id,
                    'similarity_score': score
                })
        
        # Rank and update positions
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        for rank, match in enumerate(matches, 1):
            score_obj = self.db.query(SimilarityScore).filter(
                SimilarityScore.user_id == user_id,
                SimilarityScore.job_id == match['job_id']
            ).first()
            if score_obj:
                score_obj.rank_position = rank
        
        self.db.commit()
        return matches
    
    def match_all_users_with_new_jobs(self, threshold: float = 0.75):
        """Match all users with newly added jobs"""
        users = self.db.query(User).all()
        
        for user in users:
            self.match_user_with_jobs(user.user_id, threshold)