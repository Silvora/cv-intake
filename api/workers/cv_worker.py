import asyncio

from api.services.cv_processing_service import process_cv_async


def process_cv_job(cv_id: str, file_path: str, cv_name: str, job_text: str) -> None:
    asyncio.run(process_cv_async(cv_id, file_path, cv_name, job_text))
