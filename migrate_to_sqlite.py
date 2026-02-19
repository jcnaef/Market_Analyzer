#!/usr/bin/env python3
"""
Migration script: Convert processed_jobs.csv to SQLite database
Normalizes data into the new schema structure
"""

import sqlite3
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List, Optional


class DatabaseMigrator:
    def __init__(self, db_path: str = "market_analyzer.db", csv_path: str = "processed_jobs.csv"):
        self.db_path = db_path
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
        """Connect to SQLite database and initialize schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to {self.db_path}")

    def initialize_schema(self):
        """Create tables from schema.sql"""
        schema_path = Path("schema.sql")
        if not schema_path.exists():
            raise FileNotFoundError("schema.sql not found. Please create it first.")

        with open(schema_path, "r") as f:
            schema = f.read()

        self.cursor.executescript(schema)
        self.conn.commit()
        print("✓ Database schema initialized")

    def get_or_create_skill_category(self, category_name: str) -> int:
        """Get or create skill category and return ID"""
        if category_name in self.skill_category_cache:
            return self.skill_category_cache[category_name]

        self.cursor.execute(
            "SELECT id FROM skill_categories WHERE name = ?",
            (category_name,)
        )
        result = self.cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO skill_categories (name) VALUES (?)",
                (category_name,)
            )
            category_id = self.cursor.lastrowid
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
            "SELECT id FROM skills WHERE name = ? AND category_id = ?",
            (skill_name, category_id)
        )
        result = self.cursor.fetchone()

        if result:
            skill_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO skills (name, category_id) VALUES (?, ?)",
                (skill_name, category_id)
            )
            skill_id = self.cursor.lastrowid

        self.skill_cache[key] = skill_id
        return skill_id

    def get_or_create_company(self, company_data: Dict) -> int:
        """Get or create company and return ID"""
        muse_id = str(company_data.get("company.id", ""))

        if not muse_id or muse_id == "":
            return None

        if muse_id in self.company_cache:
            return self.company_cache[muse_id]

        self.cursor.execute(
            "SELECT id FROM companies WHERE muse_company_id = ?",
            (muse_id,)
        )
        result = self.cursor.fetchone()

        if result:
            company_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO companies (muse_company_id, name, short_name) VALUES (?, ?, ?)",
                (
                    muse_id,
                    company_data.get("company.name", "Unknown"),
                    company_data.get("company.short_name", "")
                )
            )
            company_id = self.cursor.lastrowid
            self.stats["companies_created"] += 1

        self.company_cache[muse_id] = company_id
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

        location_key = (city, state, "USA", is_remote)

        if location_key in self.location_cache:
            return self.location_cache[location_key]

        self.cursor.execute(
            "SELECT id FROM locations WHERE city = ? AND state = ? AND country = ? AND is_remote = ?",
            location_key
        )
        result = self.cursor.fetchone()

        if result:
            location_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO locations (city, state, country, is_remote) VALUES (?, ?, ?, ?)",
                location_key
            )
            location_id = self.cursor.lastrowid
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
            muse_job_id = str(row.get("id", ""))
            if not muse_job_id:
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

            # Check if job already exists
            self.cursor.execute("SELECT id FROM jobs WHERE muse_job_id = ?", (muse_job_id,))
            existing_job = self.cursor.fetchone()

            if existing_job:
                # UPSERT: Update existing job
                job_id = existing_job[0]
                self.cursor.execute(
                    """UPDATE jobs SET
                        title = ?, company_id = ?, description = ?, clean_description = ?,
                        salary_min = ?, salary_max = ?, is_remote = ?, publication_date = ?,
                        job_url = ?, fetched_at = ?, updated_at = ?, status = 'open', last_seen_at = ?
                        WHERE muse_job_id = ?""",
                    (
                        row.get("name", ""),
                        company_id,
                        row.get("contents", ""),
                        row.get("clean_description", ""),
                        salary_min,
                        salary_max,
                        1 if is_remote else 0,
                        pub_date if pub_date else None,
                        row.get("refs.landing_page", ""),
                        self.run_timestamp,
                        self.run_timestamp,
                        self.run_timestamp,
                        muse_job_id
                    )
                )
                self.stats["jobs_updated"] += 1
            else:
                # INSERT: New job
                self.cursor.execute(
                    """INSERT INTO jobs (
                        muse_job_id, title, company_id, description, clean_description,
                        salary_min, salary_max, is_remote, publication_date, job_url,
                        fetched_at, last_seen_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
                    (
                        muse_job_id,
                        row.get("name", ""),
                        company_id,
                        row.get("contents", ""),
                        row.get("clean_description", ""),
                        salary_min,
                        salary_max,
                        1 if is_remote else 0,
                        pub_date if pub_date else None,
                        row.get("refs.landing_page", ""),
                        self.run_timestamp,
                        self.run_timestamp
                    )
                )
                job_id = self.cursor.lastrowid
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
                        "INSERT OR IGNORE INTO job_locations (job_id, location_id) VALUES (?, ?)",
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
                                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)",
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
                """UPDATE jobs SET status = 'closed', updated_at = ?
                   WHERE status = 'open' AND (last_seen_at IS NULL OR last_seen_at < ?)""",
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
        print("\n🚀 Starting migration from CSV to SQLite...\n")

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
    migrator = DatabaseMigrator(
        db_path="market_analyzer.db",
        csv_path="processed_jobs.csv"
    )
    migrator.migrate()
