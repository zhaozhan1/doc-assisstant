from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.middleware import register_exception_handlers


@pytest.fixture
def app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-http")
    async def raise_http():
        raise HTTPException(status_code=404, detail="资源不存在")

    @app.get("/raise-value-error")
    async def raise_value_error():
        raise ValueError("参数错误")

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_http_exception_returns_standard_format(client):
    resp = client.get("/raise-http")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "资源不存在"
    assert body["detail"] == "资源不存在"


def test_unhandled_exception_returns_500(client):
    resp = client.get("/raise-value-error")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "INTERNAL_ERROR"


def test_normal_request_passes_through(client):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
