import pandas as pd
import ast
from collections import Counter

class SkillRecommender:
    def __init__(self, csv_path):
        print("Loading data and building matrix...")
        self.df = pd.read_csv(csv_path)
        self.skill_matrix = self._build_skill_matrix()
        self.all_skills = sorted(list(self.skill_matrix.index))
        print("System ready.")

    def _build_skill_matrix(self):
        # 1. Columns that contain our skills
        skill_cols = [
            'skills_Languages', 'skills_Frameworks_Libs', 
            'skills_Tools_Infrastructure', 'skills_Concepts'
        ]
        
        # 2. Parse the stringified lists from CSV back into Python lists
        # Checks if column exists to avoid errors
        cols_to_use = [c for c in skill_cols if c in self.df.columns]
        
        for col in cols_to_use:
            self.df[col] = self.df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else []
            )

        # 3. Aggregate all skills per job
        self.df['combined_skills'] = self.df[cols_to_use].values.tolist()
        # Flatten the list of lists
        self.df['combined_skills'] = self.df['combined_skills'].apply(
            lambda x: [item.lower() for sublist in x for item in sublist]
        )

        # 4. Build Co-occurrence Matrix
        # Get unique vocabulary
        unique_skills = sorted(list(set(
            [s for sublist in self.df['combined_skills'] for s in sublist]
        )))
        
        # Initialize DataFrame
        matrix = pd.DataFrame(0, index=unique_skills, columns=unique_skills)

        # Populate counts
        for skills in self.df['combined_skills']:
            for s1 in skills:
                for s2 in skills:
                    matrix.loc[s1, s2] += 1
                    
        # Convert to Probability (Row-wise normalization)
        # "Given row skill, what is probability of col skill?"
        matrix = matrix.div(matrix.values.diagonal(), axis=0)
        return matrix
    
    def get_skill_recommendations(self, skill_name, limit=10):
        skill_name = skill_name.lower()
        
        if skill_name not in self.skill_matrix.index:
            return None
        
        # Get the specific row for this skill
        correlations = self.skill_matrix.loc[skill_name]
        
        # Sort by highest match, drop the skill itself (which is always 1.0)
        sorted_skills = correlations.sort_values(ascending=False).drop(skill_name)
        
        # Format for API
        return [
            {"skill": skill, "score": round(score, 2)}
            for skill, score in sorted_skills.head(limit).items()
        ]
