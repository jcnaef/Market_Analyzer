#!/usr/bin/env python3
"""
Migration script: Convert processed_jobs.csv to PostgreSQL database
Normalizes data into the new schema structure
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List, Optional

import psycopg2

ROOT_DIR = Path(__file__).resolve().parent.parent

# Allow importing db_config when run as a script
sys.path.insert(0, str(ROOT_DIR / "src"))
from market_analyzer.db_config import DATABASE_URL


class DatabaseMigrator:
    def __init__(self, db_url: str = None, csv_path: str = None):
        if db_url is None:
            db_url = DATABASE_URL
        if csv_path is None:
            csv_path = str(ROOT_DIR / "data" / "processed_jobs.csv")
        self.db_url = db_url
        self.csv_path = csv_path
        self.conn = None
        self.cursor = None
        self.run_timestamp = datetime.now().isoformat()

        # Cache for IDs to avoid duplicate lookups
        self.company_cache: Dict[str, int] = {}
        self.location_cache: Dict[Tuple, int] = {}
        self.skill_cache: Dict[Tuple[str, str], int] = {}  # (skill_name, category) -> id
        self.skill_category_cache: Dict[str, int] = {}

        # Statistics
        self.stats = {
            "jobs_imported": 0,
            "jobs_updated": 0,
            "companies_created": 0,
            "locations_created": 0,
            "skills_created": 0,
            "job_skills_created": 0,
            "jobs_closed": 0,
            "errors": 0
        }

    def connect(self):
        """Connect to PostgreSQL database and initialize schema"""
        self.conn = psycopg2.connect(self.db_url)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to PostgreSQL")

    def initialize_schema(self):
        """Create tables from schema.sql"""
        schema_path = ROOT_DIR / "data" / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError("schema.sql not found. Please create it first.")

        with open(schema_path, "r") as f:
            schema = f.read()

        self.cursor.execute(schema)
        self.conn.commit()
        print("✓ Database schema initialized")

    def get_or_create_skill_category(self, category_name: str) -> int:
        """Get or create skill category and return ID"""
        if category_name in self.skill_category_cache:
            return self.skill_category_cache[category_name]

        self.cursor.execute(
            "SELECT id FROM skill_categories WHERE name = %s",
            (category_name,)
        )
        result = self.cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO skill_categories (name) VALUES (%s) RETURNING id",
                (category_name,)
            )
            category_id = self.cursor.fetchone()[0]
            self.stats["skills_created"] += 1

        self.skill_category_cache[category_name] = category_id
        return category_id

    def get_or_create_skill(self, skill_name: str, category_name: str) -> int:
        """Get or create skill and return ID"""
        if not skill_name or not skill_name.strip():
            return None

        skill_name = skill_name.strip()
        key = (skill_name, category_name)

        if key in self.skill_cache:
            return self.skill_cache[key]

        category_id = self.get_or_create_skill_category(category_name)

        self.cursor.execute(
            "SELECT id FROM skills WHERE name = %s AND category_id = %s",
            (skill_name, category_id)
        )
        result = self.cursor.fetchone()

        if result:
            skill_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO skills (name, category_id) VALUES (%s, %s) RETURNING id",
                (skill_name, category_id)
            )
            skill_id = self.cursor.fetchone()[0]

        self.skill_cache[key] = skill_id
        return skill_id

    def get_or_create_company(self, company_data: Dict) -> int:
        """Get or create company and return ID"""
        company_name = company_data.get("company.name", "Unknown")

        if not company_name or company_name == "Unknown":
            return None

        if company_name in self.company_cache:
            return self.company_cache[company_name]

        self.cursor.execute(
            "SELECT id FROM companies WHERE name = %s",
            (company_name,)
        )
        result = self.cursor.fetchone()

        if result:
            company_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO companies (name, short_name) VALUES (%s, %s) RETURNING id",
                (
                    company_name,
                    company_data.get("company.short_name", "")
                )
            )
            company_id = self.cursor.fetchone()[0]
            self.stats["companies_created"] += 1

        self.company_cache[company_name] = company_id
        return company_id

    def get_or_create_location(self, job_city: List[str], is_remote: bool) -> int:
        """Get or create location and return ID"""
        # Parse location from job_city (stored as list of dicts in CSV)
        city = "Remote" if is_remote else "Unknown"
        state = None

        if job_city and isinstance(job_city, list) and len(job_city) > 0:
            location_item = job_city[0]
            # Handle both dict format {'name': 'New York, NY'} and string format
            location_str = location_item.get('name') if isinstance(location_item, dict) else location_item
            if location_str and "," in location_str:
                parts = location_str.split(",")
                city = parts[0].strip()
                state = parts[1].strip() if len(parts) > 1 else None

        location_key = (city, state, "USA")

        if location_key in self.location_cache:
            return self.location_cache[location_key]

        self.cursor.execute(
            "SELECT id FROM locations WHERE city = %s AND state = %s AND country = %s",
            location_key
        )
        result = self.cursor.fetchone()

        if result:
            location_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO locations (city, state, country) VALUES (%s, %s, %s) RETURNING id",
                location_key
            )
            location_id = self.cursor.fetchone()[0]
            self.stats["locations_created"] += 1

        self.location_cache[location_key] = location_id
        return location_id

    def parse_salary(self, salary_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse salary range from string like '$97,500.00 - $134,700.00'"""
        if not salary_str or salary_str.strip() == "":
            return None, None

        try:
            parts = salary_str.split("-")
            salary_min = float(parts[0].replace("$", "").replace(",", "").strip())
            salary_max = float(parts[1].replace("$", "").replace(",", "").strip()) if len(parts) > 1 else None
            return salary_min, salary_max
        except (ValueError, IndexError):
            return None, None

    def parse_skills_json(self, skills_json_str: str) -> Dict[str, List[str]]:
        """Parse skills JSON from CSV"""
        if not skills_json_str or skills_json_str.strip() == "":
            return {}

        try:
            return json.loads(skills_json_str.replace("'", '"'))
        except json.JSONDecodeError:
            return {}

    def import_job(self, row: Dict) -> bool:
        """Import single job row - UPSERT if exists, INSERT if new"""
        try:
            external_job_id = str(row.get("id", ""))
            if not external_job_id:
                return False

            # Get or create company
            company_id = self.get_or_create_company(row)
            if not company_id:
                return False

            # Parse salary
            salary_min, salary_max = self.parse_salary(row.get("salary", ""))

            # Parse publication date
            pub_date = row.get("publication_date", "")
            is_remote = row.get("is_remote", "").lower() == "true" or row.get("is_remote") == True

            # Check if job already exists by external ID
            self.cursor.execute("SELECT id FROM jobs WHERE external_job_id = %s", (external_job_id,))
            existing_job = self.cursor.fetchone()

            if existing_job:
                # UPSERT: Update existing job
                job_id = existing_job[0]
                self.cursor.execute(
                    """UPDATE jobs SET
                        title = %s, company_id = %s, description = %s,
                        salary_min = %s, salary_max = %s, is_remote = %s, publication_date = %s,
                        job_url = %s, fetched_at = %s, updated_at = %s, status = 'open', last_seen_at = %s
                        WHERE id = %s""",
                    (
                        row.get("name", ""),
                        company_id,
                        row.get("clean_description", ""),
                        salary_min,
                        salary_max,
                        is_remote,
                        pub_date if pub_date else None,
                        row.get("refs.landing_page", ""),
                        self.run_timestamp,
                        self.run_timestamp,
                        self.run_timestamp,
                        job_id
                    )
                )
                self.stats["jobs_updated"] += 1
            else:
                # INSERT: New job
                self.cursor.execute(
                    """INSERT INTO jobs (
                        external_job_id, title, company_id, description,
                        salary_min, salary_max, is_remote, publication_date, job_url,
                        fetched_at, last_seen_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
                    RETURNING id""",
                    (
                        external_job_id,
                        row.get("name", ""),
                        company_id,
                        row.get("clean_description", ""),
                        salary_min,
                        salary_max,
                        is_remote,
                        pub_date if pub_date else None,
                        row.get("refs.landing_page", ""),
                        self.run_timestamp,
                        self.run_timestamp
                    )
                )
                job_id = self.cursor.fetchone()[0]
                self.stats["jobs_imported"] += 1

            # Get or create ALL locations and link them to the job
            job_city_str = row.get("locations", "[]")
            try:
                job_cities = json.loads(job_city_str.replace("'", '"'))
            except:
                job_cities = []

            # If no explicit locations but job is remote, create remote location
            if not job_cities and is_remote:
                job_cities = [{"name": "Remote"}]

            # Process all locations for this job
            for job_city in job_cities:
                location_id = self.get_or_create_location([job_city], is_remote)
                if location_id:
                    self.cursor.execute(
                        """INSERT INTO job_locations (job_id, location_id) VALUES (%s, %s)
                           ON CONFLICT DO NOTHING""",
                        (job_id, location_id)
                    )

            # Parse and insert skills
            skills_data = self.parse_skills_json(row.get("skills_data", "{}"))
            skill_categories = [
                "Languages", "Frameworks_Libs", "Tools_Infrastructure", "Concepts", "Soft_Skills"
            ]

            for category in skill_categories:
                category_key = f"skills_{category}"
                if category_key in row:
                    skills_list = self.parse_skills_json(row.get(category_key, "[]"))
                    if isinstance(skills_list, list):
                        for skill_name in skills_list:
                            skill_id = self.get_or_create_skill(skill_name, category)
                            if skill_id:
                                self.cursor.execute(
                                    """INSERT INTO job_skills (job_id, skill_id) VALUES (%s, %s)
                                       ON CONFLICT DO NOTHING""",
                                    (job_id, skill_id)
                                )
                                self.stats["job_skills_created"] += 1

            return True

        except Exception as e:
            print(f"✗ Error importing job {row.get('id')}: {e}")
            self.stats["errors"] += 1
            return False

    def mark_closed_jobs(self):
        """Mark jobs as closed if they weren't seen in this run"""
        try:
            self.cursor.execute(
                """UPDATE jobs SET status = 'closed', updated_at = %s
                   WHERE status = 'open' AND (last_seen_at IS NULL OR last_seen_at < %s)""",
                (self.run_timestamp, self.run_timestamp)
            )
            self.stats["jobs_closed"] = self.cursor.rowcount
            self.conn.commit()
            if self.stats["jobs_closed"] > 0:
                print(f"✓ Marked {self.stats['jobs_closed']} jobs as closed")
        except Exception as e:
            print(f"✗ Error marking closed jobs: {e}")

    def migrate(self):
        """Run the full migration"""
        print("\n🚀 Starting migration from CSV to PostgreSQL...\n")

        self.connect()
        self.initialize_schema()

        # Check if CSV exists
        csv_path = Path(self.csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"{self.csv_path} not found")

        # Read and import CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                self.import_job(row)
                if i % 100 == 0:
                    print(f"  Processed {i} rows...")
                    self.conn.commit()

        self.conn.commit()

        # Mark jobs not seen in this run as closed
        self.mark_closed_jobs()

        self.conn.close()

        # Print statistics
        print("\n" + "="*50)
        print("✓ Migration Complete!")
        print("="*50)
        print(f"Jobs imported:      {self.stats['jobs_imported']}")
        print(f"Jobs updated:       {self.stats['jobs_updated']}")
        print(f"Jobs closed:        {self.stats['jobs_closed']}")
        print(f"Companies created:  {self.stats['companies_created']}")
        print(f"Locations created:  {self.stats['locations_created']}")
        print(f"Job-Skill links:    {self.stats['job_skills_created']}")
        print(f"Errors:             {self.stats['errors']}")
        print("="*50 + "\n")


if __name__ == "__main__":
    migrator = DatabaseMigrator()
    migrator.migrate()
