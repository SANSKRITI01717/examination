"""
API v1 router assembly.
"""
from fastapi import APIRouter

from app.api.v1.answers import router as answers_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.exams import router as exams_router
from app.api.v1.marking import router as marking_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.questions import router as questions_router
from app.api.v1.reference import router as reference_router
from app.api.v1.sheets import router as sheets_router
from app.api.v1.students import router as students_router
from app.api.v1.users import router as users_router
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.moderation import router as moderation_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(exams_router)
api_v1_router.include_router(questions_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(sheets_router)
api_v1_router.include_router(ocr_router)
api_v1_router.include_router(answers_router)
api_v1_router.include_router(evaluation_router)
api_v1_router.include_router(marking_router)
api_v1_router.include_router(reference_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(moderation_router)

from app.api.v1.analytics import router as analytics_router
from app.api.v1.results import router as results_router

api_v1_router.include_router(analytics_router)
api_v1_router.include_router(results_router)


