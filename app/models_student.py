"""SQLModel tables for the student information system, replacing the mock
JSON file (app/data/students.json) with a real (if still fictional-data)
database. Shares the engine and metadata in app/models.py - see that file
for why.

These tables are read-only from the app's perspective; nothing in Ringback
writes to them. SqlDirectory (app/directory.py) is the only place that
queries them, same boundary JSONDirectory already draws around
app/data/students.json.
"""

from datetime import date as date_
from typing import Optional

from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    student_number: str = Field(primary_key=True)
    full_name: str
    gender: Optional[str] = None
    birthdate: Optional[date_] = None
    id_number: Optional[str] = None
    marital_status: Optional[str] = None
    home_language: Optional[str] = None
    citizenship: Optional[str] = None
    email: Optional[str] = None
    cellphone: Optional[str] = None
    postal_address: Optional[str] = None
    study_address: Optional[str] = None
    disability: Optional[str] = None
    current_balance: float = 0.0


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
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


class Registration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
    qualification: Optional[str] = None
    registration_year: Optional[int] = None
    academic_block: Optional[str] = None
    offering_type: Optional[str] = None
    period_of_study: Optional[str] = None
    registration_date: Optional[date_] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    has_bursary: bool = False


class SubjectEnrolment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
    subject_code: str
    description: Optional[str] = None
    academic_block: Optional[str] = None
    offering_type: Optional[str] = None
    class_group: Optional[str] = None
    prac_group: Optional[str] = None
    tut_group: Optional[str] = None
    attendance: Optional[str] = None
    cancel_date: Optional[date_] = None
    drop_deadline: Optional[date_] = None
    att_proj: Optional[float] = None
    exam_granted: Optional[bool] = None
    exam_month: Optional[str] = None
    half_period: Optional[bool] = None
    full_period: Optional[bool] = None
    final_mark: Optional[float] = None
    result: Optional[str] = None
    withheld_reasons: Optional[str] = None


class FeeLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
    date: Optional[date_] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None


class AgeAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
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


class Bursary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_number: str = Field(foreign_key="student.student_number")
    year: Optional[int] = None
    bursary_code: Optional[str] = None
    description: Optional[str] = None
    is_nsfas: bool = False
    awarded: Optional[float] = None
    allocated: Optional[float] = None
    unallocated: Optional[float] = None
