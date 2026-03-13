import psycopg2
from market_analyzer.db_config import DATABASE_URL

def investigate_salary_outliers(threshold=800000):
    """
    Fetches and prints job descriptions for jobs with unusually high salaries.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Join with companies table to get the name for better context
        query = """
            SELECT j.title, c.name, j.salary_min, j.salary_max, j.description, j.external_job_id
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            WHERE j.salary_max >= %s
            ORDER BY j.salary_max DESC
        """
        
        cursor.execute(query, (threshold,))
        rows = cursor.fetchall()

        if not rows:
            print(f"No jobs found with a salary max >= ${threshold:,}")
            return

        print(f"\n--- Found {len(rows)} Outliers (Threshold: ${threshold:,}) ---\n")

        for title, company, s_min, s_max, desc, ext_id in rows:
            print("=" * 80)
            print(f"TITLE:   {title}")
            print(f"COMPANY: {company}")
            print(f"SALARY:  ${s_min:,.2f} - ${s_max:,.2f}")
            print(f"ID:      {ext_id}")
            print("-" * 40)
            print("DESCRIPTION (FULL):")
            print(desc)
            print("=" * 80 + "\n")

    except Exception as e:
        print(f"Error connecting to database: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # You can adjust the threshold here to see different levels of outliers
    investigate_salary_outliers(threshold=1000000)
