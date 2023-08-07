import base64
import io
import json
import time
import traceback
from copy import deepcopy
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf
from celery_backend.tasks import log_data
from custom_metrics import INFERENCE_REQUEST_COUNT, INFERENCE_REQUEST_DURATION_SECONDS
from exception.base_error import BaseError
from exception.client_error import ClientError
from exception.null_value_error import NullValueError
from fastapi import Depends, Request, status
from pydub import AudioSegment
from schema.services.common import (
    LANG_CODE_TO_SCRIPT_CODE,
    AudioFormat,
    _ULCAAudio,
    _ULCABaseAudioConfig,
    _ULCALanguage,
    _ULCATaskType,
    _ULCAText,
)
from schema.services.request import (
    ULCAAsrInferenceRequest,
    ULCAGenericInferenceRequest,
    ULCAInferenceRequest,
    ULCANerInferenceRequest,
    ULCAPipelineInferenceRequest,
    ULCATranslationInferenceRequest,
    ULCATransliterationInferenceRequest,
    ULCATtsInferenceRequest,
)
from schema.services.request.ulca_asr_inference_request import ULCATextFormat
from schema.services.response import (
    ULCAAsrInferenceResponse,
    ULCAInferenceResponse,
    ULCANerInferenceResponse,
    ULCAPipelineInferenceResponse,
    ULCATranslationInferenceResponse,
    ULCATransliterationInferenceResponse,
    ULCATtsInferenceResponse,
)
from scipy.io import wavfile

from ..error.errors import Errors
from ..gateway import InferenceGateway
from ..model import Model, ModelCache, Service, ServiceCache
from ..repository import ModelRepository, ServiceRepository
from .audio_service import AudioService
from .post_processor_service import PostProcessorService
from .subtitle_service import SubtitleService
from .triton_utils_service import TritonUtilsService


def populate_service_cache(serviceId: str, service_repository: ServiceRepository):
    service = service_repository.get_by_service_id(serviceId)
    service_cache = ServiceCache(**service.dict())
    service_cache.save()
    return service_cache


def populate_model_cache(modelId: str, model_repository: ModelRepository):
    model = model_repository.get_by_id(modelId)
    model_cache = ModelCache(**model.dict())
    model_cache.save()
    return model_cache


def validate_service_id(serviceId: str, service_repository):
    try:
        service = ServiceCache.get(serviceId)
    except Exception:
        try:
            service = populate_service_cache(serviceId, service_repository)
        except NullValueError:
            raise ClientError(
                status_code=status.HTTP_404_BAD_REQUEST, message="Invalid Service Id"
            )
        except Exception:
            raise BaseError(Errors.DHRUVA104.value, traceback.format_exc())

    return service


def validate_model_id(modelId: str, model_repository):
    try:
        model = ModelCache.get(modelId)
    except Exception:
        try:
            model = populate_model_cache(modelId, model_repository)
        except Exception:
            raise BaseError(Errors.DHRUVA105.value, traceback.format_exc())

    return model


class InferenceService:
    def __init__(
        self,
        service_repository: ServiceRepository = Depends(ServiceRepository),
        model_repository: ModelRepository = Depends(ModelRepository),
        inference_gateway: InferenceGateway = Depends(InferenceGateway),
        subtitle_service: SubtitleService = Depends(SubtitleService),
        post_processor_service: PostProcessorService = Depends(PostProcessorService),
        audio_service: AudioService = Depends(AudioService),
        triton_utils_service: TritonUtilsService = Depends(TritonUtilsService),
    ) -> None:
        self.service_repository = service_repository
        self.model_repository = model_repository
        self.inference_gateway = inference_gateway
        self.subtitle_service = subtitle_service
        self.post_processor_service = post_processor_service
        self.audio_service = audio_service
        self.triton_utils_service = triton_utils_service

    async def run_inference(
        self,
        request: ULCAInferenceRequest,
        request_state: Request,
    ) -> ULCAInferenceResponse:
        serviceId = request.config.serviceId
        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        model: Model = validate_model_id(service.modelId, self.model_repository)  # type: ignore

        task_type = model.task.type
        request_body = request.dict()

        match task_type:
            case _ULCATaskType.TRANSLATION:
                request_obj = ULCATranslationInferenceRequest(**request_body)
                return await self.run_translation_triton_inference(
                    request_obj, request_state
                )
            case _ULCATaskType.TRANSLITERATION:
                request_obj = ULCATransliterationInferenceRequest(**request_body)
                return await self.run_transliteration_triton_inference(
                    request_obj, request_state
                )
            case _ULCATaskType.ASR:
                request_obj = ULCAAsrInferenceRequest(**request_body)
                return await self.run_asr_triton_inference(request_obj, request_state)
            case _ULCATaskType.TTS:
                request_obj = ULCATtsInferenceRequest(**request_body)
                return await self.run_tts_triton_inference(request_obj, request_state)
            case _ULCATaskType.NER:
                request_obj = ULCANerInferenceRequest(**request_body)
                return await self.run_ner_triton_inference(request_obj, request_state)
            case _:
                raise BaseError(Errors.DHRUVA115.value)

    async def run_asr_triton_inference(
        self,
        request_body: ULCAAsrInferenceRequest,
        request_state: Request,
    ) -> ULCAAsrInferenceResponse:
        serviceId = request_body.config.serviceId

        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        headers = {"Authorization": "Bearer " + service.api_key}

        language = request_body.config.language.sourceLanguage
        lm_enabled = (
            "lm" in request_body.config.postProcessors
            if request_body.config.postProcessors
            else False
        )
        model_name = "asr_am_lm_ensemble" if lm_enabled else "asr_am_ensemble"
        standard_rate = 16000

        res = ULCAAsrInferenceResponse(output=[])
        for input in request_body.audio:
            file_bytes = self.__get_audio_bytes(input)
            file_handle = io.BytesIO(file_bytes)

            final_audio = self.__process_asr_input(file_handle, standard_rate)

            # TODO: Specialised chunked inference for Whisper since it is unstable for long audio at high throughput
            batch_size, chunk_size = (1, 16) if "whisper" in serviceId else (32, 20)

            audio_chunks, speech_timestamps = self.audio_service.silero_vad_chunking(
                final_audio,
                standard_rate,
                max_chunk_duration_s=chunk_size,
                min_chunk_duration_s=6.0,
            )

            transcript_lines: List[Tuple[str, Dict[str, float]]] = []
            for i in range(0, len(audio_chunks), batch_size):
                batch = audio_chunks[i : i + batch_size]
                inputs, outputs = self.triton_utils_service.get_asr_io_for_triton(
                    batch, serviceId, language
                )

                response = await self.inference_gateway.send_triton_request(
                    url=service.endpoint,
                    model_name=model_name,
                    input_list=inputs,
                    output_list=outputs,
                    headers=headers,
                    request_state=request_state,
                    task_type="asr",
                    request_body=request_body,
                )

                encoded_result = response.as_numpy("TRANSCRIPTS")
                if encoded_result is None:
                    encoded_result = np.array([])

                transcript_lines.extend(
                    [
                        (result.decode("utf-8"), speech_timestamps[i + idx])
                        for idx, result in enumerate(encoded_result.tolist())
                    ]
                )

            if request_body.config.postProcessors:
                transcript_lines = await self.__run_asr_post_processors(
                    transcript_lines,
                    request_body.config.postProcessors,
                    request_body.config.language.sourceLanguage,
                    request_state,
                )

            transcript = self.__create_asr_response_format(
                transcript_lines, request_body.config.transcriptionFormat.value
            )

            res.output.append(_ULCAText(source=transcript.strip()))

        return res

    async def run_translation_triton_inference(
        self,
        request_body: ULCATranslationInferenceRequest,
        request_state: Request,
    ) -> ULCATranslationInferenceResponse:
        serviceId = request_body.config.serviceId

        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        headers = {"Authorization": "Bearer " + service.api_key}

        source_lang = request_body.config.language.sourceLanguage
        target_lang = request_body.config.language.targetLanguage

        # TODO: Make Triton itself accept script-code separately
        if (
            request_body.config.language.sourceScriptCode
            and source_lang in LANG_CODE_TO_SCRIPT_CODE
            and request_body.config.language.sourceScriptCode
            != LANG_CODE_TO_SCRIPT_CODE[source_lang]
        ):
            source_lang += "_" + request_body.config.language.sourceScriptCode

        if (
            request_body.config.language.targetScriptCode
            and target_lang in LANG_CODE_TO_SCRIPT_CODE
            and request_body.config.language.targetScriptCode
            != LANG_CODE_TO_SCRIPT_CODE[target_lang]
        ):
            target_lang += "_" + request_body.config.language.targetScriptCode

        input_texts = [
            input.source.replace("\n", " ").strip() if input.source else " "
            for input in request_body.input
        ]

        inputs, outputs = self.triton_utils_service.get_translation_io_for_triton(
            input_texts, source_lang, target_lang
        )

        response = await self.inference_gateway.send_triton_request(
            url=service.endpoint,
            model_name="nmt",
            input_list=inputs,
            output_list=outputs,
            headers=headers,
            request_state=request_state,
            task_type="translation",
            request_body=request_body,
        )

        encoded_result = response.as_numpy("OUTPUT_TEXT")
        if encoded_result is None:
            encoded_result = np.array([])

        output_batch = encoded_result.tolist()

        results = []
        for source_text, result in zip(input_texts, output_batch):
            results.append({"source": source_text, "target": result[0].decode("utf-8")})

        return ULCATranslationInferenceResponse(output=results)

    async def run_transliteration_triton_inference(
        self,
        request_body: ULCATransliterationInferenceRequest,
        request_state: Request,
    ) -> ULCATransliterationInferenceResponse:
        serviceId = request_body.config.serviceId

        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        headers = {"Authorization": "Bearer " + service.api_key}

        results = []
        source_lang = request_body.config.language.sourceLanguage
        target_lang = request_body.config.language.targetLanguage
        is_word_level = not request_body.config.isSentence
        top_k = request_body.config.numSuggestions

        for input in request_body.input:
            input_string = input.source.replace("\n", " ").strip()
            if input_string:
                (
                    inputs,
                    outputs,
                ) = self.triton_utils_service.get_transliteration_io_for_triton(
                    input_string, source_lang, target_lang, is_word_level, top_k
                )

                response = await self.inference_gateway.send_triton_request(
                    url=service.endpoint,
                    model_name="transliteration",
                    input_list=inputs,
                    output_list=outputs,
                    headers=headers,
                    request_state=request_state,
                    task_type="transliteration",
                    request_body=request_body,
                )

                encoded_result = response.as_numpy("OUTPUT_TEXT")
                if encoded_result is None:
                    encoded_result = np.array([np.array([])])

                result = [r.decode("utf-8") for r in encoded_result.tolist()[0]]
            else:
                result = [input_string]

            results.append({"source": input_string, "target": result})

        return ULCATransliterationInferenceResponse(output=results)

    async def run_tts_triton_inference(
        self,
        request_body: ULCATtsInferenceRequest,
        request_state: Request,
    ) -> ULCATtsInferenceResponse:
        serviceId = request_body.config.serviceId

        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        headers = {"Authorization": "Bearer " + service.api_key}

        ip_language = request_body.config.language.sourceLanguage
        ip_gender = request_body.config.gender.value
        standard_rate = 22050
        target_sr = (
            22050
            if not request_body.config.samplingRate
            else request_body.config.samplingRate
        )
        format = (
            "s16le"
            if request_body.config.audioFormat == AudioFormat.PCM
            else request_body.config.audioFormat.value
        )

        results = []

        for input in request_body.input:
            input_string = self.__process_tts_input(input.source)

            if input_string:
                inputs, outputs = self.triton_utils_service.get_tts_io_for_triton(
                    input_string, ip_gender, ip_language
                )

                response = await self.inference_gateway.send_triton_request(
                    url=service.endpoint,
                    model_name="tts",
                    input_list=inputs,
                    output_list=outputs,
                    headers=headers,
                    request_state=request_state,
                    task_type="tts",
                    request_body=request_body,
                )

                result = response.as_numpy("OUTPUT_GENERATED_AUDIO")
                if result is None:
                    result = np.array([np.array([])])

                raw_audio = result[0]
                resampled_audio = self.audio_service.resample_audio(
                    raw_audio, standard_rate, target_sr
                )

                byte_io = io.BytesIO()
                wavfile.write(byte_io, target_sr, resampled_audio)

                if format != "wav":
                    AudioSegment.from_file_using_temporary_files(byte_io).export(
                        byte_io, format=format
                    )

                encoded_bytes = base64.b64encode(byte_io.read())
                encoded_string = encoded_bytes.decode()
            else:
                encoded_string = ""

            results.append(_ULCAAudio(audioContent=encoded_string))

        base_audio_config = _ULCABaseAudioConfig(
            language=_ULCALanguage(sourceLanguage=ip_language),
            audioFormat=request_body.config.audioFormat,
            encoding="base64",
            samplingRate=target_sr,
        )

        return ULCATtsInferenceResponse(audio=results, config=base_audio_config)

    async def run_ner_triton_inference(
        self,
        request_body: ULCANerInferenceRequest,
        request_state: Request,
    ) -> ULCANerInferenceResponse:
        serviceId = request_body.config.serviceId

        service: Service = validate_service_id(serviceId, self.service_repository)  # type: ignore
        headers = {"Authorization": "Bearer " + service.api_key}

        # TODO: Replace with real deployments
        res = self.inference_gateway.send_inference_request(
            request_body=request_body,
            service=service,
            request_state=request_state,
            task_type="ner",
        )

        return ULCANerInferenceResponse(**res)

    async def run_pipeline_inference(
        self,
        request_body: ULCAPipelineInferenceRequest,
        request_state: Request,  # for request state
    ) -> ULCAPipelineInferenceResponse:
        results = []

        # Check if the pipeline construction is valid
        is_pipeline_valid = True
        for i in range(len(request_body.pipelineTasks) - 1):
            current_task_type, next_task_type = (
                request_body.pipelineTasks[i].taskType,
                request_body.pipelineTasks[i + 1].taskType,
            )
            if current_task_type == _ULCATaskType.ASR:
                if next_task_type not in {_ULCATaskType.TRANSLATION}:
                    is_pipeline_valid = False
                    break
            elif current_task_type == _ULCATaskType.TRANSLATION:
                if next_task_type not in {_ULCATaskType.TTS}:
                    is_pipeline_valid = False
                    break
            elif current_task_type == _ULCATaskType.TRANSLITERATION:
                if next_task_type not in {_ULCATaskType.TRANSLATION, _ULCATaskType.TTS}:
                    is_pipeline_valid = False
                    break
                if (
                    "isSentence" in request_body.pipelineTasks[i].config
                    and not request_body.pipelineTasks[i].config["isSentence"]
                ):
                    # Word-level does not make sense in pipeline
                    is_pipeline_valid = False
                    break
            else:
                is_pipeline_valid = False
                break

        if not is_pipeline_valid:
            # TODO: Return proper error messages once standardized
            return {"pipelineResponse": results}

        data_tracking_consent = False
        previous_output_json = request_body.inputData.dict()
        for pipeline_task in request_body.pipelineTasks:
            serviceId = (
                pipeline_task.config["serviceId"]
                if "serviceId" in pipeline_task.config
                else None
            )
            if not serviceId:
                serviceId = self.__auto_select_service_id(
                    pipeline_task.taskType, pipeline_task.config
                )

            start_time = time.perf_counter()
            new_request = ULCAGenericInferenceRequest(
                config=pipeline_task.config,
                **previous_output_json,
                controlConfig=request_body.controlConfig,
            )
            new_request.config.serviceId = serviceId

            error_msg, exception = None, None
            try:
                api_key_id = str(
                    request_state.state.api_key_id
                )  # Having this here to capture all errors
                previous_output_json = await self.run_inference(
                    request=new_request,
                    request_state=request_state,
                )
            except BaseError as exc:
                exception = exc
                if exc.error_kind in (
                    Errors.DHRUVA101.value["kind"],
                    Errors.DHRUVA102.value["kind"],
                ):
                    error_msg = exc.error_kind + "_" + exc.error_message
            except Exception as other_exception:
                exception = other_exception
                error_msg = str(other_exception)

            if request_state.state._state.get("api_key_data_tracking"):
                data_tracking_consent = True
                if (
                    new_request.controlConfig
                    and new_request.controlConfig.dataTracking is False
                ):
                    data_tracking_consent = False

            log_data.apply_async(
                (
                    pipeline_task.taskType,
                    serviceId,
                    request_state.headers.get(
                        "X-Forwarded-For", request_state.client.host
                    ),
                    data_tracking_consent,
                    error_msg,
                    api_key_id,
                    new_request.json(),
                    # Error in first task will result in a dict, not pydantic model response
                    json.dumps(previous_output_json)
                    if isinstance(previous_output_json, dict)
                    else previous_output_json.json(),
                    time.perf_counter() - start_time,
                ),
                queue="data_log",
            )
            if exception:
                raise exception

            results.append(deepcopy(previous_output_json))

            # Output of previous will be input for next
            previous_output_json = previous_output_json.dict()
            previous_output_json.pop("config", None)
            if "output" in previous_output_json:
                previous_output_json["input"] = previous_output_json["output"]
                del previous_output_json["output"]

                if pipeline_task.taskType == _ULCATaskType.TRANSLATION:
                    # The output (target) of translation should be input (source) to next
                    for i in range(len(previous_output_json["input"])):
                        previous_output_json["input"][i][
                            "source"
                        ] = previous_output_json["input"][i]["target"]
                        del previous_output_json["input"][i]["target"]
                elif pipeline_task.taskType == _ULCATaskType.TRANSLITERATION:
                    # The first output (target) of xlit should be input (source) to next
                    for i in range(len(previous_output_json["input"])):
                        previous_output_json["input"][i][
                            "source"
                        ] = previous_output_json["input"][i]["target"][0]
                        del previous_output_json["input"][i]["target"]
            else:
                # This will ideally happen only for TTS, which is the final task supported *as of now*
                pass
        return {"pipelineResponse": results}

    def __get_audio_bytes(self, input: _ULCAAudio):
        try:
            if input.audioContent:
                file_bytes = base64.b64decode(input.audioContent)
            else:  # Either input audioContent or audioUri have to exist. Validation in Pydantic class.
                file_bytes = self.audio_service.download_audio(input.audioUri)  # type: ignore
        except Exception:
            raise BaseError(Errors.DHRUVA116.value, traceback.format_exc())

        return file_bytes

    def __process_asr_input(self, file_handle: io.BytesIO, standard_rate: int):
        data, sampling_rate = sf.read(file_handle)
        data = data.tolist()
        raw_audio = np.array(data)  # in float64

        mono_raw_audio = self.audio_service.stereo_to_mono(raw_audio)
        resampled_audio = self.audio_service.resample_audio(
            mono_raw_audio, sampling_rate, standard_rate
        )
        equalized_audio = self.audio_service.equalize_amplitude(
            resampled_audio, standard_rate
        )
        final_audio = self.audio_service.dequantize_audio(equalized_audio)

        return final_audio

    async def __run_asr_post_processors(
        self,
        transcript_lines: List[Tuple[str, Dict[str, float]]],
        post_processors: List[str],
        source_language: str,
        request_state: Request,
    ):
        for idx, transcript_line in enumerate(transcript_lines):
            line = transcript_line[0]
            if "itn" in post_processors:
                line = await self.post_processor_service.run_itn(
                    line,
                    source_language,
                    request_state,
                )

            if "punctuation" in post_processors:
                line = await self.post_processor_service.run_itn(
                    line,
                    source_language,
                    request_state,
                )

            new_transcript_line = (line, transcript_line[1])
            transcript_lines[idx] = new_transcript_line

        return transcript_lines

    def __create_asr_response_format(
        self,
        transcript_lines: List[Tuple[str, Dict[str, float]]],
        transcription_format: ULCATextFormat,
    ):
        transcript = ""
        match transcription_format:
            case ULCATextFormat.SRT:
                transcript += self.subtitle_service.get_srt_subtitle(transcript_lines)
            case ULCATextFormat.WEBVTT:
                transcript += self.subtitle_service.get_webvtt_subtitle(
                    transcript_lines
                )
            case ULCATextFormat.TRANSCRIPT:
                for line in transcript_lines:
                    transcript += line[0].strip() + " "

        return transcript

    def __process_tts_input(self, text: str):
        processed_text = text.replace("।", ".").strip()
        return processed_text

    def __auto_select_service_id(
        self, task_type: _ULCATaskType, config: Dict[str, Any]
    ) -> str:
        match task_type:
            case _ULCATaskType.ASR:
                if config["language"]["sourceLanguage"] == "en":
                    serviceId = "ai4bharat/whisper-medium-en--gpu--t4"
                elif config["language"]["sourceLanguage"] == "hi":
                    serviceId = "ai4bharat/conformer-hi-gpu--t4"
                elif config["language"]["sourceLanguage"] in {"kn", "ml", "ta", "te"}:
                    serviceId = "ai4bharat/conformer-multilingual-dravidian-gpu--t4"
                else:
                    serviceId = "ai4bharat/conformer-multilingual-indo_aryan-gpu--t4"
            case _ULCATaskType.TRANSLATION:
                serviceId = "ai4bharat/indictrans-v2-all-gpu--t4"
            case _ULCATaskType.TTS:
                if config["language"]["sourceLanguage"] in {"kn", "ml", "ta", "te"}:
                    serviceId = "ai4bharat/indic-tts-coqui-dravidian-gpu--t4"
                elif config["language"]["sourceLanguage"] in {"en", "brx", "mni"}:
                    serviceId = "ai4bharat/indic-tts-coqui-misc-gpu--t4"
                else:
                    serviceId = "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4"
            case _:
                raise BaseError(Errors.DHRUVA115.value)

        return serviceId
