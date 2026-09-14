import os

# Every test in this suite expects the locally seeded ringback.db (see
# scripts/seed_students.py --target sqlite - several tests reference its
# specific demo students by number and fail with a clear message if it
# hasn't been run). .env now also carries a real Neon DATABASE_URL (needed
# for --target postgres and for running the backend locally against
# production data), and load_dotenv() only fills in variables that aren't
# already set - so without this, the whole suite would silently start
# reading from and writing to the live production database instead,
# depending on nothing more than import order. Setting it here, before any
# test module or app.models import happens (pytest always loads conftest.py
# first), pins the suite to the local file no matter what.
os.environ["DATABASE_URL"] = "sqlite:///./campusops.db"

