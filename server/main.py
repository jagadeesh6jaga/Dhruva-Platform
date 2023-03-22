from logging.config import dictConfig
from typing import Callable, Union

from fastapi import FastAPI, Request
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info

from exception.base_error import BaseError
from exception.ulca_api_key_client_error import ULCAApiKeyClientError
from exception.ulca_api_key_server_error import ULCAApiKeyServerError
from log.logger import LogConfig
from fastapi.logger import logger
from logging.config import dictConfig
from module import *
from seq_streamer import StreamingServerTaskSequence

dictConfig(LogConfig().dict())

app = FastAPI(
    title="Dhruva API",
    description="Backend API for communicating with the Dhruva platform",
)

streamer = StreamingServerTaskSequence()
app.mount("/socket.io", streamer.app)

# TODO: Depreciate this soon in-favor of above
from asr_streamer import StreamingServerASR
streamer_asr = StreamingServerASR()
# Mount it at an alternative path. 
app.mount("/socket_asr.io", streamer_asr.app)

app.include_router(ServicesApiRouter)
app.include_router(AuthApiRouter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# def http_body_language() -> Callable[[Info], None]:
#     METRIC = Counter(
#         "http_body_language", "Number of times a certain language has been requested.", labelnames=("langs",)
#     )

#     def instrumentation(info: Info) -> None:
#         lang_str = info.request.body['langs']
#         METRIC.labels(langs=lang_str).inc()

#     return instrumentation


# @app.on_event("startup")
# async def load_prometheus():
#     Instrumentator().instrument(app).add(http_body_language()).expose(app)


@app.exception_handler(ULCAApiKeyClientError)
async def ulca_api_key_client_error_handler(
    request: Request, exc: ULCAApiKeyClientError
):
    return JSONResponse(
        status_code=exc.error_code,
        content={
            "isRevoked": False,
            "message": exc.message,
        },
    )


@app.exception_handler(ULCAApiKeyServerError)
async def ulca_api_key_server_error_handler(
    request: Request, exc: ULCAApiKeyServerError
):
    logger.error(exc)

    return JSONResponse(
        status_code=500,
        content={
            "isRevoked": False,
            "message": exc.error_kind + " - Internal Server Error",
        },
    )


@app.exception_handler(BaseError)
async def base_error_handler(request: Request, exc: BaseError):
    logger.error(exc)

    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "kind": exc.error_kind,
                "message": f"Request failed. Please try again.",
            }
        },
    )


@app.get("/")
def read_root():
    return "Welcome to Dhruva API!"

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5050, log_level="info", workers=2)
