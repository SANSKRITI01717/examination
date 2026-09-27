from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, register_error_handlers


def create_test_app() -> FastAPI:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/trigger-app-error")
    def trigger_app_error():
        raise AppError(
            code="EXAM_LOCKED",
            message="Cannot modify exam while in evaluation status",
            status_code=409,
            details={"exam_id": 123},
        )

    class SampleBody(BaseModel):
        score: int

    @test_app.post("/trigger-validation-error")
    def trigger_validation_error(body: SampleBody):
        return {"score": body.score}

    @test_app.get("/trigger-unhandled-error")
    def trigger_unhandled_error():
        raise RuntimeError("Unexpected failure in processing")

    return test_app


test_client = TestClient(create_test_app(), raise_server_exceptions=False)


def test_app_error_response_format():
    response = test_client.get("/trigger-app-error")
    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EXAM_LOCKED"
    assert data["error"]["message"] == "Cannot modify exam while in evaluation status"
    assert data["error"]["details"] == {"exam_id": 123}


def test_validation_error_response_format():
    response = test_client.post("/trigger-validation-error", json={"score": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert "errors" in data["error"]["details"]


def test_not_found_response_format():
    response = test_client.get("/non-existent-path")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


def test_unhandled_error_response_format_no_stack_trace():
    response = test_client.get("/trigger-unhandled-error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Ensure stack trace is not leaked
    assert "Unexpected failure in processing" not in str(data)
    assert data["error"]["message"] == "An unexpected server error occurred."
