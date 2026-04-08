# Backfill script to find jobs with missing salary data in the database
# and attempt to extract salary info from their descriptions using regex.

import psycopg2
import re
from market_analyzer.db_config import DATABASE_URL
# Import the existing parser from your collector
from collector import _parse_google_salary

def extract_salary(text):
    """
    Attempts to pull salary ranges using Regex. 
    Improved to capture context (like 'hour' or 'year') to help the parser.
    """
    if not text:
        return None
    
    # This pattern looks for the $ range and up to 15 characters after it 
    # to catch 'an hour' or 'per year' for the parser to see.
    pattern = r'(\$[0-9][0-9,\.]*[kK]?\s*(?:-|to)?\s*\$?[0-9][0-9,\.]*[kK]?)(.{0,15})'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        # Combine the range and the suffix context (e.g., "$50 - $70 an hour")
        return f"{match.group(1)} {match.group(2)}"
    return None

# Queries the database for jobs missing salary data and updates them using regex extraction
def backfill_missing_salaries():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # 1. Find jobs missing salary data
    print("Searching for jobs with missing salary data...")
    cursor.execute("SELECT id, description FROM jobs WHERE salary_min IS NULL OR salary_max IS NULL")
    jobs_to_fix = cursor.fetchall()
    
    print(f"Found {len(jobs_to_fix)} jobs to process.")
    
    updated_count = 0
    
    for job_id, description in jobs_to_fix:
        # 2. Extract string from description
        raw_salary_str = extract_salary(description)
        
        if raw_salary_str:
            # 3. Convert string to numbers using your existing collector logic
            s_min, s_max = _parse_google_salary(raw_salary_str)
            
            if s_min or s_max:
                # 4. Update the database
                cursor.execute(
                    "UPDATE jobs SET salary_min = %s, salary_max = %s WHERE id = %s",
                    (s_min, s_max, job_id)
                )
                updated_count += 1
                if updated_count % 10 == 0:
                    print(f"Updated {updated_count} jobs...")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Finished! Successfully updated salary data for {updated_count} jobs.")

if __name__ == "__main__":
    backfill_missing_salaries()
