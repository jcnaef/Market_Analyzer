import pandas as pd
import ast

class LocationSkillRecommender:
    def __init__(self, csv_path):
        print(f"Loading location data from {csv_path}...")
        self.df = pd.read_csv(csv_path)
        self.location_matrix = self._build_location_matrix()
        print("Location system ready.")

    def _build_location_matrix(self):
        print("Building Location Matrix...")
        expanded_rows = []
        
        # Columns that contain skills
        skill_cols = [
            'skills_Languages', 'skills_Frameworks_Libs', 
            'skills_Tools_Infrastructure', 'skills_Concepts'
        ]
        
        # Iterate through every job to map Location -> Skills
        for index, row in self.df.iterrows():
            # 1. Gather all skills for this job
            skills = []
            for col in skill_cols:
                if col in self.df.columns and pd.notna(row[col]):
                    val = row[col]
                    # Parse string "['python']" -> list ['python']
                    if isinstance(val, str):
                        try:
                            skills.extend(ast.literal_eval(val))
                        except:
                            pass
                    elif isinstance(val, list):
                        skills.extend(val)
            
            # Lowercase for consistency
            skills = [s.lower() for s in skills]
            
            if not skills:
                continue

            # 2. Get Cities (Parse from string "['NY', 'Seattle']")
            raw_cities = row.get('job_city', "[]")
            current_cities = []
            if isinstance(raw_cities, str):
                try:
                    current_cities = ast.literal_eval(raw_cities)
                except:
                    current_cities = []
            elif isinstance(raw_cities, list):
                current_cities = raw_cities

            # 3. Add entry for each Physical City
            for city in current_cities:
                for skill in skills:
                    expanded_rows.append({"Location": city, "Skill": skill})
            
            # 4. Add entry for Remote (if applicable)
            is_remote = row.get('is_remote', False)
            if str(is_remote).lower() == 'true' or is_remote is True:
                for skill in skills:
                    expanded_rows.append({"Location": "Remote", "Skill": skill})
        
        # 5. Build Crosstab
        if not expanded_rows:
            return pd.DataFrame()
            
        loc_df = pd.DataFrame(expanded_rows)
        return pd.crosstab(loc_df['Location'], loc_df['Skill'])

    def get_location_trends(self, location_name, limit=10):
        search_term = location_name.lower()
        
        # Exact match first (e.g. "Remote")
        matches = [loc for loc in self.location_matrix.index if loc.lower() == search_term]
        
        # Partial match fallback (e.g. "york" -> "New York")
        if not matches:
            matches = [loc for loc in self.location_matrix.index if search_term in loc.lower()]
            
        if not matches:
            return None
            
        target_loc = matches[0]
        skills_row = self.location_matrix.loc[target_loc]
        
        # Sort by count
        top_skills = skills_row.sort_values(ascending=False).head(limit)
        
        return {
            "location": target_loc,
            "top_skills": [
                {"skill": skill, "count": int(count)} 
                for skill, count in top_skills.items() if count > 0
            ]
        }
