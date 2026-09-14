"""Seed the student directory tables (app/models_student.py) with fictional
but realistic NUST data - replaces app/data/students.json's mock JSON.

    python scripts/seed_students.py --target sqlite
    python scripts/seed_students.py --target postgres   # requires DATABASE_URL set

--target sqlite always seeds the local ringback.db regardless of what's in
the environment, so you can't accidentally seed a real Neon database by
forgetting to unset DATABASE_URL. --target postgres requires DATABASE_URL
to already point at postgres - it won't silently fall back to sqlite.

No real phone numbers here - every cellphone below is a placeholder. Set
your own number via the RINGBACK_TEST_PHONE env var and pass it to the
intake form directly when testing live; it never needs to be committed.
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _students():
    """Ten specific demo cases first (each proving one mechanism), then
    ten filler students for volume/realism. See CLAUDE.md / README for
    which case demonstrates what.
    """
    from app.models_student import (
        AgeAnalysis,
        Application,
        Bursary,
        FeeLine,
        Registration,
        Student,
        SubjectEnrolment,
    )

    FACULTIES = [
        "Faculty of Computing and Informatics",
        "Faculty of Engineering and the Built Environment",
        "Faculty of Health, Natural Resources and Applied Sciences",
        "Faculty of Commerce, Human Sciences and Education",
    ]

    students, applications, registrations = [], [], []
    subjects, fee_lines, age_analyses, bursaries = [], [], [], []

    def add_student(**kw):
        kw.setdefault("gender", "F")
        kw.setdefault("marital_status", "Single")
        kw.setdefault("citizenship", "Namibian")
        kw.setdefault("disability", None)
        # home_language has no default on purpose - it used to, and every
        # call below omitted it, so all 20 fictional students silently came
        # out Oshiwambo-speaking. Namibia has many language communities
        # (Otjiherero, Khoekhoegowab, Rukwangali, Silozi, Setswana, Afrikaans
        # among them); a demo roster that erases all of them by default is a
        # real bias, not a neutral placeholder. Every caller must now state
        # it explicitly.
        students.append(Student(**kw))

    # 1. Clean record, zero balance, everything resolves.
    add_student(
        student_number="220100001",
        full_name="Ndinelago Amakali",
        home_language="Oshiwambo",
        birthdate=date(2003, 4, 12),
        id_number="03041200123",
        email="namakali@nust.na",
        cellphone="+264810000001",
        postal_address="P.O. Box 1001, Windhoek",
        study_address="Hage Heights, Windhoek",
        current_balance=0.0,
    )
    applications.append(
        Application(
            student_number="220100001", academic_year=2025, qualification="Bachelor of Computer Science",
            description="Bachelor of Computer Science", academic_preference=1, wrs_score=32,
            contract_code="07BCMS", admission_status="accepted", faculty=FACULTIES[0],
            department="School of Computing",
        )
    )
    registrations.append(
        Registration(
            student_number="220100001", qualification="Bachelor of Computer Science", registration_year=2025,
            academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 1",
            registration_date=date(2026, 2, 3), faculty=FACULTIES[0], department="School of Computing",
            has_bursary=False,
        )
    )
    subjects.append(
        SubjectEnrolment(
            student_number="220100001", subject_code="CSC612S", description="Software Engineering",
            academic_block="Semester 1", class_group="A", attendance="Good",
            drop_deadline=date(2026, 9, 5), att_proj=78, exam_granted=True, exam_month="November",
            final_mark=74, result="Pass",
        )
    )
    age_analyses.append(AgeAnalysis(student_number="220100001", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 2. Registered but blocked by an outstanding balance (proof-of-reg case).
    add_student(
        student_number="220100002",
        full_name="Hafeni Amutenya",
        gender="M",
        home_language="Oshiwambo",
        birthdate=date(2002, 11, 3),
        id_number="02110300456",
        email="hamutenya@nust.na",
        cellphone="+264810000002",
        postal_address="P.O. Box 1002, Windhoek",
        study_address="Katutura, Windhoek",
        current_balance=2340.00,
    )
    registrations.append(
        Registration(
            student_number="220100002", qualification="Bachelor of Computer Science", registration_year=2025,
            academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
            registration_date=date(2026, 7, 10), faculty=FACULTIES[0], department="School of Computing",
        )
    )
    subjects.append(
        SubjectEnrolment(
            student_number="220100002", subject_code="CSC612S", description="Software Engineering",
            academic_block="Semester 2", class_group="B", drop_deadline=date(2026, 9, 5),
        )
    )
    fee_lines.append(
        FeeLine(student_number="220100002", date=date(2026, 7, 15), reference="TUITION2025S2",
                description="Semester 2 tuition fee", debit=2340.00, balance=2340.00)
    )
    age_analyses.append(
        AgeAnalysis(student_number="220100002", days_60=1200.0, days_30=1140.0, current=0.0,
                    balance=2340.00, date_of_balance=date(2026, 8, 1))
    )

    # 3. One subject past its drop deadline, another still inside it.
    add_student(
        student_number="220100003",
        full_name="Uandjisa Kavari",
        home_language="Otjiherero",
        birthdate=date(2003, 6, 20),
        id_number="03062000789",
        email="ukavari@nust.na",
        cellphone="+264810000003",
        postal_address="P.O. Box 1003, Windhoek",
        study_address="Khomasdal, Windhoek",
        current_balance=0.0,
    )
    registrations.append(
        Registration(
            student_number="220100003", qualification="Bachelor of Science", registration_year=2025,
            academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
            registration_date=date(2026, 7, 8), faculty=FACULTIES[2], department="School of Natural and Applied Sciences",
        )
    )
    subjects.append(
        SubjectEnrolment(student_number="220100003", subject_code="MAT621S", description="Numerical Methods",
                          academic_block="Semester 2", drop_deadline=date(2026, 8, 15))  # already past
    )
    subjects.append(
        SubjectEnrolment(student_number="220100003", subject_code="PHY611S", description="Applied Physics",
                          academic_block="Semester 2", drop_deadline=date(2026, 9, 12))  # still open
    )
    age_analyses.append(AgeAnalysis(student_number="220100003", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 4. Results withheld due to an outstanding balance.
    add_student(
        student_number="220100004",
        full_name="Johannes Shikongo",
        gender="M",
        home_language="Oshiwambo",
        birthdate=date(2001, 9, 14),
        id_number="01091400234",
        email="jshikongo@nust.na",
        cellphone="+264810000004",
        postal_address="P.O. Box 1004, Windhoek",
        study_address="Wanaheda, Windhoek",
        current_balance=4100.00,
    )
    registrations.append(
        Registration(student_number="220100004", qualification="Bachelor of Accounting", registration_year=2025,
                     academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
                     registration_date=date(2026, 7, 5), faculty=FACULTIES[3],
                     department="Department of Economics, Accounting and Finance")
    )
    subjects.append(
        SubjectEnrolment(student_number="220100004", subject_code="ACC611S", description="Financial Accounting 2",
                          academic_block="Semester 2", final_mark=68, result="Pass",
                          withheld_reasons="Outstanding fee balance")
    )
    fee_lines.append(
        FeeLine(student_number="220100004", date=date(2026, 2, 1), reference="TUITION2025S1",
                description="Semester 1 tuition fee", debit=4100.00, balance=4100.00)
    )
    age_analyses.append(
        AgeAnalysis(student_number="220100004", days_160=4100.0, balance=4100.00,
                    date_of_balance=date(2026, 8, 1))
    )

    # 5. Bursary awarded with a large unallocated portion.
    add_student(
        # Khoekhoegowab (Damara/Nama) surnames are gendered - "-ab" is the
        # masculine form, "-as" the feminine one (e.g. Uirab / Uiras). Selma
        # is a woman, hence Uiras, not Uirab.
        student_number="220100005",
        full_name="Karere Uiras",
        home_language="Khoekhoegowab",
        birthdate=date(2003, 1, 30),
        id_number="03013000567",
        email="kuiras@nust.na",
        cellphone="+264810000005",
        postal_address="P.O. Box 1005, Windhoek",
        study_address="Otjomuise, Windhoek",
        current_balance=0.0,
    )
    registrations.append(
        Registration(student_number="220100005", qualification="Bachelor of Engineering in Civil Engineering",
                     registration_year=2025, academic_block="Full Year", offering_type="Full-time",
                     period_of_study="Semester 2", registration_date=date(2026, 7, 9), faculty=FACULTIES[1],
                     department="Department of Civil, Mining and Process Engineering", has_bursary=True)
    )
    bursaries.append(
        Bursary(student_number="220100005", year=2025, bursary_code="NSFAS-2025", description="NSFAS Bursary",
                is_nsfas=True, awarded=45000.00, allocated=18000.00, unallocated=27000.00)
    )
    age_analyses.append(AgeAnalysis(student_number="220100005", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 6. Exam entry denied on low attendance/project mark.
    add_student(
        student_number="220100006",
        full_name="Erastus Sitentu",
        gender="M",
        home_language="Rukwangali",
        birthdate=date(2002, 5, 8),
        id_number="02050800890",
        email="esitentu@nust.na",
        cellphone="+264810000006",
        postal_address="P.O. Box 1006, Windhoek",
        study_address="Rocky Crest, Windhoek",
        current_balance=0.0,
    )
    registrations.append(
        Registration(student_number="220100006", qualification="Bachelor of Human Nutrition", registration_year=2025,
                     academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
                     registration_date=date(2026, 7, 11), faculty=FACULTIES[2],
                     department="School of Health Sciences")
    )
    subjects.append(
        SubjectEnrolment(student_number="220100006", subject_code="NUT621S", description="Community Nutrition",
                          academic_block="Semester 2", attendance="Below 60% required", att_proj=42,
                          exam_granted=False, exam_month="November")
    )
    age_analyses.append(AgeAnalysis(student_number="220100006", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 7. Application cancelled with a stated reason.
    add_student(
        student_number="220100007",
        full_name="Nangula Nekundi",
        home_language="Oshiwambo",
        birthdate=date(2004, 2, 17),
        id_number="04021700345",
        email="nnekundi@nust.na",
        cellphone="+264810000007",
        postal_address="P.O. Box 1007, Windhoek",
        study_address="Not yet registered",
        current_balance=0.0,
    )
    applications.append(
        Application(student_number="220100007", academic_year=2025, qualification="Bachelor of Architecture",
                    description="Bachelor of Architecture", academic_preference=1, wrs_score=27,
                    admission_status="cancelled", cancel_date=date(2026, 1, 20),
                    cancel_reason="Did not meet the minimum points requirement for the programme",
                    faculty=FACULTIES[1], department="Department of Architecture, Planning and Construction")
    )
    age_analyses.append(AgeAnalysis(student_number="220100007", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 8. Credit balance (institution owes them).
    add_student(
        student_number="220100008",
        full_name="Petrina Uushona",
        home_language="Oshiwambo",
        birthdate=date(2003, 10, 25),
        id_number="03102500678",
        email="puushona@nust.na",
        cellphone="+264810000008",
        postal_address="P.O. Box 1008, Windhoek",
        study_address="Pionierspark, Windhoek",
        current_balance=-850.00,
    )
    registrations.append(
        Registration(student_number="220100008", qualification="Bachelor of Marketing", registration_year=2025,
                     academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
                     registration_date=date(2026, 7, 7), faculty=FACULTIES[3],
                     department="Department of Marketing, Logistics and Sport Management")
    )
    fee_lines.append(
        FeeLine(student_number="220100008", date=date(2026, 7, 20), reference="REFUND-SUBJDROP",
                description="Refund for dropped subject", credit=850.00, balance=-850.00)
    )
    age_analyses.append(
        AgeAnalysis(student_number="220100008", credit=850.00, balance=-850.00, date_of_balance=date(2026, 8, 1))
    )

    # 9. Disability flag set - to prove it is never disclosed.
    add_student(
        student_number="220100009",
        full_name="Ottilie Haingura",
        home_language="Rukwangali",
        birthdate=date(2002, 8, 2),
        id_number="02080200901",
        email="ohaingura@nust.na",
        cellphone="+264810000009",
        postal_address="P.O. Box 1009, Windhoek",
        study_address="Cimbebasia, Windhoek",
        disability="Visual impairment - registered with Student Support for exam accommodations",
        current_balance=0.0,
    )
    registrations.append(
        Registration(student_number="220100009", qualification="Bachelor of English and Linguistics",
                     registration_year=2025, academic_block="Full Year", offering_type="Full-time",
                     period_of_study="Semester 2", registration_date=date(2026, 7, 6), faculty=FACULTIES[3],
                     department="Department of Communication and Languages")
    )
    age_analyses.append(AgeAnalysis(student_number="220100009", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 10. Two applications, second preference accepted.
    add_student(
        student_number="220100010",
        full_name="Immanuel Katjivena",
        gender="M",
        home_language="Otjiherero",
        birthdate=date(2003, 3, 11),
        id_number="03031100112",
        email="ikatjivena@nust.na",
        cellphone="+264810000010",
        postal_address="P.O. Box 1010, Windhoek",
        study_address="Dorado Park, Windhoek",
        current_balance=0.0,
    )
    applications.append(
        Application(student_number="220100010", academic_year=2025, qualification="Bachelor of Engineering in Mechanical Engineering",
                    description="Bachelor of Engineering in Mechanical Engineering", academic_preference=1,
                    wrs_score=34, admission_status="rejected", faculty=FACULTIES[1],
                    department="Department of Mechanical, Industrial and Electrical Engineering")
    )
    applications.append(
        Application(student_number="220100010", academic_year=2025, qualification="Bachelor of Technology in Mechanical Engineering",
                    description="Bachelor of Technology in Mechanical Engineering", academic_preference=2,
                    wrs_score=34, admission_status="accepted", faculty=FACULTIES[1],
                    department="Department of Mechanical, Industrial and Electrical Engineering")
    )
    registrations.append(
        Registration(student_number="220100010", qualification="Bachelor of Technology in Mechanical Engineering",
                     registration_year=2025, academic_block="Full Year", offering_type="Full-time",
                     period_of_study="Semester 2", registration_date=date(2026, 7, 9), faculty=FACULTIES[1],
                     department="Department of Mechanical, Industrial and Electrical Engineering")
    )
    age_analyses.append(AgeAnalysis(student_number="220100010", balance=0.0, date_of_balance=date(2026, 8, 1)))

    # 11-20: filler students for volume/realism - simpler, still complete.
    # home_language varies deliberately - Namibia has many language
    # communities (Oshiwambo is the largest, but far from the only one), and
    # a filler roster that's silently 100% one of them is exactly the bias
    # this file used to have by default (see add_student() above). Names mix
    # traditional and English first names deliberately (both are genuinely
    # common in Namibia, not an either/or), and a couple of students
    # deliberately share a first name or surname with someone else on the
    # roster - unrelated people sharing a name is normal, not a data bug.
    filler = [
        ("220100011", "Aina Shivute", "F", "Oshiwambo", "Bachelor of Informatics", FACULTIES[0], 0.0),
        ("220100012", "Frans Mukwiilongo", "M", "Oshiwambo", "Bachelor of Public Management", FACULTIES[3], 620.0),
        ("220100013", "Namukolo Sitali", "F", "Silozi", "Bachelor of Land Administration", FACULTIES[1], 0.0),
        ("220100014", "Sacky Shivute", "M", "Oshiwambo", "Bachelor of Environmental Health Science", FACULTIES[2], 1500.0),
        ("220100015", "Loide Nekongo", "F", "Oshiwambo", "Bachelor of Business Management", FACULTIES[3], 0.0),
        ("220100016", "Johannes Moeng", "M", "Setswana", "Bachelor of Geomatics", FACULTIES[1], 0.0),
        ("220100017", "Ndapewa Amwaama", "F", "Oshiwambo", "Bachelor of Applied Mathematics and Statistics", FACULTIES[2], 0.0),
        ("220100018", "Petrus Tjombe", "M", "Otjiherero", "Bachelor of Entrepreneurship", FACULTIES[3], 300.0),
        ("220100019", "Elizabeth Beukes", "F", "Afrikaans", "Bachelor of Computer Science in Cyber Security", FACULTIES[0], 0.0),
        ("220100020", "Gabriel Tjitunga", "M", "Otjiherero", "Bachelor of Science", FACULTIES[2], 0.0),
    ]
    for i, (num, name, gender, language, qual, faculty, balance) in enumerate(filler):
        add_student(
            student_number=num, full_name=name, gender=gender, home_language=language,
            birthdate=date(2002 + (i % 3), 1 + (i % 12), 1 + (i % 27)),
            id_number=f"0{2 + i % 3}0{1 + i % 9}0{1 + i % 27:02d}{100 + i}",
            email=f"{name.split()[0][0].lower()}{name.split()[1].lower()}@nust.na",
            cellphone=f"+26481000{11 + i:03d}",
            postal_address=f"P.O. Box {1011 + i}, Windhoek",
            study_address="Windhoek",
            current_balance=balance,
        )
        registrations.append(
            Registration(student_number=num, qualification=qual, registration_year=2025,
                         academic_block="Full Year", offering_type="Full-time", period_of_study="Semester 2",
                         registration_date=date(2026, 7, 5 + (i % 10)), faculty=faculty,
                         department=faculty.replace("Faculty of ", "School of "))
        )
        if balance > 0:
            fee_lines.append(
                FeeLine(student_number=num, date=date(2026, 7, 15), reference="TUITION2025S2",
                        description="Semester 2 tuition fee", debit=balance, balance=balance)
            )
        age_analyses.append(
            AgeAnalysis(student_number=num, days_30=balance, balance=balance, date_of_balance=date(2026, 8, 1))
        )

    return students, applications, registrations, subjects, fee_lines, age_analyses, bursaries


def build(target: str) -> None:
    if target == "postgres":
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            print("--target postgres requires DATABASE_URL to already point at a postgres database.")
            raise SystemExit(1)
    else:
        # Force local sqlite regardless of what's in the environment, so
        # this can't accidentally seed a real Neon database by forgetting
        # to unset DATABASE_URL.
        os.environ.pop("DATABASE_URL", None)

    from sqlmodel import Session, delete

    from app.models import engine, init_db
    from app.models_student import (
        AgeAnalysis,
        Application,
        Bursary,
        FeeLine,
        Registration,
        Student,
        SubjectEnrolment,
    )

    init_db()
    students, applications, registrations, subjects, fee_lines, age_analyses, bursaries = _students()

    with Session(engine) as session:
        # Clear only the tables this script owns, in FK-safe order - never
        # touches Case or any other table.
        for model in (Bursary, AgeAnalysis, FeeLine, SubjectEnrolment, Registration, Application, Student):
            session.exec(delete(model))
        session.commit()

        # Students committed on their own, before anything that references
        # them. SQLite never enforces foreign keys by default, so a single
        # combined add-everything-then-commit silently worked there; Postgres
        # enforces them properly and rejected it (ageanalysis inserted before
        # its student row existed) - explicit two-phase commit instead of
        # relying on SQLAlchemy's automatic cross-table ordering.
        for row in students:
            session.add(row)
        session.commit()

        for row in applications + registrations + subjects + fee_lines + age_analyses + bursaries:
            session.add(row)
        session.commit()

    print(f"Seeded {len(students)} students to {engine.url.render_as_string(hide_password=True)}")
    print("Fee-blocked demo student for proof-of-registration testing: 220100002")
    print("Set RINGBACK_TEST_PHONE to your own number to test live - it isn't stored here.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["sqlite", "postgres"], default="sqlite")
    args = parser.parse_args()
    build(args.target)
