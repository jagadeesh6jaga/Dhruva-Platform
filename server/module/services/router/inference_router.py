import json
import time
from typing import Any, Callable, Dict, Union

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute, Request, Response

from auth.api_key_type_authorization_provider import ApiKeyTypeAuthorizationProvider
from auth.auth_provider import AuthProvider
from celery_backend.tasks import log_data
from exception.base_error import BaseError
from exception.http_error import HttpErrorResponse
from schema.auth.common import ApiKeyType
from schema.services.request import (
    ULCAAsrInferenceRequest,
    ULCAGenericInferenceRequest,
    ULCAInferenceQuery,
    ULCANerInferenceRequest,
    ULCAPipelineInferenceRequest,
    ULCAS2SInferenceRequest,
    ULCATranslationInferenceRequest,
    ULCATransliterationInferenceRequest,
    ULCATtsInferenceRequest,
)
from schema.services.response import (
    ULCAAsrInferenceResponse,
    ULCAGenericInferenceResponse,
    ULCANerInferenceResponse,
    ULCAPipelineInferenceResponse,
    ULCAS2SInferenceResponse,
    ULCATranslationInferenceResponse,
    ULCATransliterationInferenceResponse,
    ULCATtsInferenceResponse,
)

from ..error import Errors

# from ..repository import ServiceRepository, ModelRepository
from ..service.inference_service import InferenceService


class InferenceLoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def logging_route_handler(request: Request) -> Response:
            req_body_bytes = await request.body()
            req_body = req_body_bytes.decode("utf-8")
            enable_tracking = False

            start_time = time.time()
            api_key_id, res_body, error_msg = None, None, None
            try:
                response: Response = await original_route_handler(request)
                res_body = response.body
                api_key_id = str(
                    request.state.api_key_id
                )  # Having this here to capture all errors

            except BaseError as exc:
                if exc.error_kind in (
                    Errors.DHRUVA101.value["kind"],
                    Errors.DHRUVA102.value["kind"],
                ):
                    error_msg = exc.error_kind + "_" + exc.error_message
                raise exc

            except Exception as other_exception:
                error_msg = str(other_exception)
                raise other_exception

            finally:
                if request.state._state.get("api_key_data_tracking"):
                    req_json: Dict[str, Any] = json.loads(req_body)
                    enable_tracking = req_json.get(
                        "controlConfig", {"dataTracking": True}
                    )["dataTracking"]

                url_components = request.url._url.split("?serviceId=")
                if len(url_components) == 2:
                    usage_type, service_component = url_components
                    usage_type = usage_type.split("/")[-1]
                    service_id = service_component.replace("%2F", "/")
                    log_data.apply_async(
                        (
                            usage_type,
                            service_id,
                            request.headers.get("X-Forwarded-For", request.client.host),
                            enable_tracking,
                            error_msg,
                            api_key_id,
                            request.state._state.get("input", req_body),
                            res_body.decode("utf-8") if res_body else None,
                            time.time() - start_time,
                        ),
                        queue="data_log",
                    )

            return response

        return logging_route_handler


router = APIRouter(
    prefix="/inference",
    route_class=InferenceLoggingRoute,
    dependencies=[
        Depends(AuthProvider),
        Depends(ApiKeyTypeAuthorizationProvider(ApiKeyType.INFERENCE)),
    ],
    responses={
        "401": {"model": HttpErrorResponse},
        "403": {"model": HttpErrorResponse},
    },
)


# For ULCA compatibility. Commenting it out temporarily
# @router.post("", response_model=ULCAGenericInferenceResponse)
# async def _run_inference_generic(
#     request: Union[
#         ULCAGenericInferenceRequest,
#         ULCAAsrInferenceRequest,
#         ULCATranslationInferenceRequest,
#         ULCATtsInferenceRequest,
#     ],
#     params: ULCAInferenceQuery = Depends(),
#     inference_service: InferenceService = Depends(InferenceService),
# ):
#     return await inference_service.run_inference(request, params.serviceId)


@router.post("/translation", response_model=ULCATranslationInferenceResponse)
async def _run_inference_translation(
    request: ULCATranslationInferenceRequest,
    params: ULCAInferenceQuery = Depends(),
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_translation_triton_inference(
        request, params.serviceId
    )


@router.post("/transliteration", response_model=ULCATransliterationInferenceResponse)
async def _run_inference_transliteration(
    request: ULCATransliterationInferenceRequest,
    params: ULCAInferenceQuery = Depends(),
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_transliteration_triton_inference(
        request, params.serviceId
    )


@router.post("/asr", response_model=ULCAAsrInferenceResponse)
async def _run_inference_asr(
    request: ULCAAsrInferenceRequest,
    params: ULCAInferenceQuery = Depends(),
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_asr_triton_inference(request, params.serviceId)


@router.post("/tts", response_model=ULCATtsInferenceResponse)
async def _run_inference_tts(
    request: ULCATtsInferenceRequest,
    params: ULCAInferenceQuery = Depends(),
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_tts_triton_inference(request, params.serviceId)


@router.post("/ner", response_model=ULCANerInferenceResponse)
async def _run_inference_ner(
    request: ULCANerInferenceRequest,
    params: ULCAInferenceQuery = Depends(),
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_ner_triton_inference(request, params.serviceId)


# Temporary endpoint; will be removed/standardized soon


@router.post("/s2s", response_model=ULCAS2SInferenceResponse)
async def _run_inference_sts(
    request: ULCAS2SInferenceRequest,
    inference_service: InferenceService = Depends(InferenceService),
):
    if request.config.language.sourceLanguage == "en":
        serviceId = "ai4bharat/conformer-en-gpu--t4"
    elif request.config.language.sourceLanguage == "hi":
        serviceId = "ai4bharat/conformer-hi-gpu--t4"
    elif request.config.language.sourceLanguage in {"kn", "ml", "ta", "te"}:
        serviceId = "ai4bharat/conformer-multilingual-dravidian-gpu--t4"
    else:
        serviceId = "ai4bharat/conformer-multilingual-indo_aryan-gpu--t4"

    asr_response = await inference_service.run_asr_triton_inference(request, serviceId)

    translation_request = ULCATranslationInferenceRequest(
        config=request.config,
        input=asr_response.output,
        controlConfig=request.controlConfig,
    )
    translation_response = await inference_service.run_translation_triton_inference(
        translation_request, "ai4bharat/indictrans-fairseq-all-gpu--t4"
    )

    for i in range(len(translation_response.output)):
        translation_response.output[i].source, translation_response.output[i].target = (
            translation_response.output[i].target,
            translation_response.output[i].source,
        )

    request.config.language.sourceLanguage = request.config.language.targetLanguage
    if request.config.language.sourceLanguage in {"kn", "ml", "ta", "te"}:
        serviceId = "ai4bharat/indic-tts-coqui-dravidian-gpu--t4"
    elif request.config.language.sourceLanguage in {"en", "brx", "mni"}:
        serviceId = "ai4bharat/indic-tts-coqui-misc-gpu--t4"
    else:
        serviceId = "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4"

    tts_request = ULCATtsInferenceRequest(
        config=request.config,
        input=translation_response.output,
        controlConfig=request.controlConfig,
    )
    tts_response = await inference_service.run_tts_triton_inference(
        tts_request, serviceId
    )

    for i in range(len(translation_response.output)):
        translation_response.output[i].source, translation_response.output[i].target = (
            translation_response.output[i].target,
            translation_response.output[i].source,
        )

    response = ULCAS2SInferenceResponse(
        output=translation_response.output,
        audio=tts_response.audio,
        config=tts_response.config,
    )

    return response


@router.post("/s2s_new_mt", response_model=ULCAS2SInferenceResponse)
async def _run_inference_sts_new_mt(
    request: ULCAS2SInferenceRequest,
    inference_service: InferenceService = Depends(InferenceService),
):
    if request.config.language.sourceLanguage == "en":
        serviceId = "ai4bharat/whisper-medium-en--gpu--t4"
    elif request.config.language.sourceLanguage == "hi":
        serviceId = "ai4bharat/conformer-hi-gpu--t4"
    elif request.config.language.sourceLanguage in {"kn", "ml", "ta", "te"}:
        serviceId = "ai4bharat/conformer-multilingual-dravidian-gpu--t4"
    else:
        serviceId = "ai4bharat/conformer-multilingual-indo_aryan-gpu--t4"

    asr_response = await inference_service.run_asr_triton_inference(request, serviceId)

    translation_request = ULCATranslationInferenceRequest(
        config=request.config,
        input=asr_response.output,
        controlConfig=request.controlConfig,
    )
    translation_response = await inference_service.run_translation_triton_inference(
        translation_request, "ai4bharat/indictrans-v2-all-gpu--t4"
    )

    for i in range(len(translation_response.output)):
        translation_response.output[i].source, translation_response.output[i].target = (
            translation_response.output[i].target,
            translation_response.output[i].source,
        )

    request.config.language.sourceLanguage = request.config.language.targetLanguage
    if request.config.language.sourceLanguage in {"kn", "ml", "ta", "te"}:
        serviceId = "ai4bharat/indic-tts-coqui-dravidian-gpu--t4"
    elif request.config.language.sourceLanguage in {"en", "brx", "mni"}:
        serviceId = "ai4bharat/indic-tts-coqui-misc-gpu--t4"
    else:
        serviceId = "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4"

    tts_request = ULCATtsInferenceRequest(
        config=request.config,
        input=translation_response.output,
        controlConfig=request.controlConfig,
    )
    tts_response = await inference_service.run_tts_triton_inference(
        tts_request, serviceId
    )

    for i in range(len(translation_response.output)):
        translation_response.output[i].source, translation_response.output[i].target = (
            translation_response.output[i].target,
            translation_response.output[i].source,
        )

    response = ULCAS2SInferenceResponse(
        output=translation_response.output,
        audio=tts_response.audio,
        config=tts_response.config,
    )

    return response


@router.post("/pipeline", response_model=ULCAPipelineInferenceResponse)
async def _run_inference_pipeline(
    request: ULCAPipelineInferenceRequest,
    request_state: Request,
    inference_service: InferenceService = Depends(InferenceService),
):
    return await inference_service.run_pipeline_inference(request, request_state)
