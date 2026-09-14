"""Institutional Directory Service for CampusOps AI.

Provides unified lookup for Students, Faculty Advisors, Department Offices, and
Financial Aid Authorities across the institution.
"""

import json
from datetime import date as date_
from pathlib import Path
from typing import List, Optional, Protocol, Dict

from pydantic import BaseModel
from sqlmodel import Session, select

STUDENTS_DATA_PATH = Path(__file__).parent / "data" / "students.json"
FACULTY_DATA_PATH = Path(__file__).parent / "data" / "faculty.json"
OFFICES_DATA_PATH = Path(__file__).parent / "data" / "offices.json"


def format_currency(amount: float) -> str:
    """Formats financial figures consistently for voice prompts and summaries."""
    if amount < 0:
        return f"a credit of N${abs(amount):,.2f}"
    return f"N${amount:,.2f}"


class Subject(BaseModel):
    code: str
    name: str
    drop_deadline: str


class Student(BaseModel):
    student_number: str
    name: str
    phone: str
    registration_status: str
    fee_balance: float
    subjects: List[Subject] = []


class Faculty(BaseModel):
    faculty_id: str
    name: str
    title: str
    department: str
    faculty: str
    phone: str
    email: str
    office_location: str
    advising_hours: str
    preferred_contact_method: str = "phone"


class Office(BaseModel):
    office_key: str
    name: str
    department: str
    officer_name: str
    phone: str
    email: str
    location: str
    hours: str
    handles: str


class ApplicationInfo(BaseModel):
    academic_year: Optional[int] = None
    qualification: Optional[str] = None
    description: Optional[str] = None
    academic_preference: Optional[int] = None
    wrs_score: Optional[int] = None
    contract_code: Optional[str] = None
    quote_number: Optional[str] = None
    quote_total: Optional[float] = None
    admission_status: Optional[str] = None
    cancel_date: Optional[date_] = None
    cancel_reason: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None


class RegistrationInfo(BaseModel):
    qualification: Optional[str] = None
    registration_year: Optional[int] = None
    academic_block: Optional[str] = None
    offering_type: Optional[str] = None
    period_of_study: Optional[str] = None
    registration_date: Optional[date_] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    has_bursary: bool = False


class SubjectDetail(BaseModel):
    subject_code: str
    description: Optional[str] = None
    academic_block: Optional[str] = None
    class_group: Optional[str] = None
    prac_group: Optional[str] = None
    tut_group: Optional[str] = None
    attendance: Optional[str] = None
    cancel_date: Optional[date_] = None
    drop_deadline: Optional[date_] = None
    att_proj: Optional[float] = None
    exam_granted: Optional[bool] = None
    exam_month: Optional[str] = None
    final_mark: Optional[float] = None
    result: Optional[str] = None
    withheld_reasons: Optional[str] = None


class FeeLineInfo(BaseModel):
    date: Optional[date_] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None


class AgeAnalysisInfo(BaseModel):
    days_160: float = 0.0
    days_90: float = 0.0
    days_60: float = 0.0
    days_30: float = 0.0
    current: float = 0.0
    credit: float = 0.0
    future: float = 0.0
    unallocated: float = 0.0
    balance: float = 0.0
    date_of_balance: Optional[date_] = None


class BursaryInfo(BaseModel):
    year: Optional[int] = None
    bursary_code: Optional[str] = None
    description: Optional[str] = None
    is_nsfas: bool = False
    awarded: Optional[float] = None
    allocated: Optional[float] = None
    unallocated: Optional[float] = None


class StudentRecord(Student):
    full_name: str
    gender: Optional[str] = None
    birthdate: Optional[date_] = None
    id_number: Optional[str] = None
    marital_status: Optional[str] = None
    home_language: Optional[str] = None
    citizenship: Optional[str] = None
    email: Optional[str] = None
    postal_address: Optional[str] = None
    study_address: Optional[str] = None
    disability: Optional[str] = None

    applications: List[ApplicationInfo] = []
    registrations: List[RegistrationInfo] = []
    subject_details: List[SubjectDetail] = []
    fee_lines: List[FeeLineInfo] = []
    age_analysis: Optional[AgeAnalysisInfo] = None
    bursaries: List[BursaryInfo] = []


class CampusDirectory(Protocol):
    def lookup_student(self, student_number: str) -> Optional[StudentRecord]: ...
    def lookup_faculty(self, faculty_id_or_name: str) -> Optional[Faculty]: ...
    def lookup_office(self, office_key: str) -> Optional[Office]: ...
    def list_faculty(self) -> List[Faculty]: ...
    def list_offices(self) -> List[Office]: ...


class SqlCampusDirectory:
    """Unified Directory supporting SQL-backed students and institutional registry."""

    def __init__(self, engine=None):
        if engine is None:
            from .models import engine as default_engine
            engine = default_engine
        self._engine = engine
        self._load_memory_cache()

    def _load_memory_cache(self):
        self._fallback_students: Dict[str, Student] = {}
        if STUDENTS_DATA_PATH.exists():
            records = json.loads(STUDENTS_DATA_PATH.read_text(encoding="utf-8"))
            self._fallback_students = {r["student_number"]: Student(**r) for r in records}

        self._faculty: Dict[str, Faculty] = {}
        if FACULTY_DATA_PATH.exists():
            faculty_records = json.loads(FACULTY_DATA_PATH.read_text(encoding="utf-8"))
            for f in faculty_records:
                obj = Faculty(**f)
                self._faculty[obj.faculty_id] = obj
                self._faculty[obj.name.lower()] = obj

        self._offices: Dict[str, Office] = {}
        if OFFICES_DATA_PATH.exists():
            office_records = json.loads(OFFICES_DATA_PATH.read_text(encoding="utf-8"))
            for o in office_records:
                obj = Office(**o)
                self._offices[obj.office_key] = obj
                self._offices[obj.name.lower()] = obj

    def lookup_student(self, student_number: str) -> Optional[StudentRecord]:
        from . import models_student as m

        try:
            with Session(self._engine) as session:
                row = session.get(m.Student, student_number)
                if row is not None:
                    registrations = session.exec(
                        select(m.Registration).where(m.Registration.student_number == student_number)
                    ).all()
                    applications = session.exec(
                        select(m.Application).where(m.Application.student_number == student_number)
                    ).all()
                    subject_rows = session.exec(
                        select(m.SubjectEnrolment).where(
                            m.SubjectEnrolment.student_number == student_number
                        )
                    ).all()
                    fee_rows = session.exec(
                        select(m.FeeLine).where(m.FeeLine.student_number == student_number)
                    ).all()
                    age_row = session.exec(
                        select(m.AgeAnalysis).where(m.AgeAnalysis.student_number == student_number)
                    ).first()
                    bursary_rows = session.exec(
                        select(m.Bursary).where(m.Bursary.student_number == student_number)
                    ).all()

                    subjects = [
                        Subject(
                            code=s.subject_code,
                            name=s.description or s.subject_code,
                            drop_deadline=str(s.drop_deadline) if s.drop_deadline else "",
                        )
                        for s in subject_rows
                    ]

                    return StudentRecord(
                        student_number=row.student_number,
                        name=row.full_name,
                        full_name=row.full_name,
                        phone=row.cellphone or "",
                        registration_status="registered" if registrations else "not_registered",
                        fee_balance=row.current_balance,
                        subjects=subjects,
                        gender=row.gender,
                        birthdate=row.birthdate,
                        id_number=row.id_number,
                        marital_status=row.marital_status,
                        home_language=row.home_language,
                        citizenship=row.citizenship,
                        email=row.email,
                        postal_address=row.postal_address,
                        study_address=row.study_address,
                        disability=row.disability,
                        applications=[ApplicationInfo(**a.model_dump()) for a in applications],
                        registrations=[RegistrationInfo(**r.model_dump()) for r in registrations],
                        subject_details=[
                            SubjectDetail(**s.model_dump(exclude={"id", "student_number"}))
                            for s in subject_rows
                        ],
                        fee_lines=[
                            FeeLineInfo(**f.model_dump(exclude={"id", "student_number"}))
                            for f in fee_rows
                        ],
                        age_analysis=(
                            AgeAnalysisInfo(**age_row.model_dump(exclude={"id", "student_number"}))
                            if age_row
                            else None
                        ),
                        bursaries=[
                            BursaryInfo(**b.model_dump(exclude={"id", "student_number"}))
                            for b in bursary_rows
                        ],
                    )
        except Exception:
            pass

        # Fallback to JSON records if SQL table is not available
        fallback = self._fallback_students.get(student_number)
        if fallback:
            return StudentRecord(
                student_number=fallback.student_number,
                name=fallback.name,
                full_name=fallback.name,
                phone=fallback.phone,
                registration_status=fallback.registration_status,
                fee_balance=fallback.fee_balance,
                subjects=fallback.subjects,
            )
        return None

    # Legacy alias for backward compatibility
    def lookup(self, student_number: str) -> Optional[StudentRecord]:
        return self.lookup_student(student_number)

    def lookup_faculty(self, identifier: str) -> Optional[Faculty]:
        key = identifier.strip().lower()
        if identifier in self._faculty:
            return self._faculty[identifier]
        if key in self._faculty:
            return self._faculty[key]
        for f in self._faculty.values():
            if key in f.name.lower() or key in f.department.lower():
                return f
        return None

    def lookup_office(self, identifier: str) -> Optional[Office]:
        key = identifier.strip().lower()
        if identifier in self._offices:
            return self._offices[identifier]
        if key in self._offices:
            return self._offices[key]
        for o in self._offices.values():
            if key in o.office_key.lower() or key in o.name.lower() or key in o.department.lower():
                return o
        return None

    def list_faculty(self) -> List[Faculty]:
        seen = set()
        out = []
        for f in self._faculty.values():
            if f.faculty_id not in seen:
                seen.add(f.faculty_id)
                out.append(f)
        return out

    def list_offices(self) -> List[Office]:
        seen = set()
        out = []
        for o in self._offices.values():
            if o.office_key not in seen:
                seen.add(o.office_key)
                out.append(o)
        return out


# Backward compatibility classes
class JSONDirectory:
    """Legacy JSON file directory reader."""
    def __init__(self, path: Optional[Path] = None):
        self._path = path or STUDENTS_DATA_PATH
        self._students: Dict[str, Student] = {}
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    s = Student(**item)
                    self._students[s.student_number] = s

    def lookup(self, student_number: str) -> Optional[Student]:
        return self._students.get(student_number)


# Default singleton instance
directory = SqlCampusDirectory()
SqlDirectory = SqlCampusDirectory

