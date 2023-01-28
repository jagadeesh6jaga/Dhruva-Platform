import traceback
from fastapi import Depends
from exception.base_error import BaseError
from ..domain.request.ulca_asr_inference_request import ULCAAsrInferenceRequest
from ..domain.request.ulca_translation_inference_request import ULCATranslationInferenceRequest
from ..domain.request.ulca_tts_inference_request import ULCATtsInferenceRequest
from ..error.errors import Errors
from ..domain.constants import DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID, LANG_TRANS_MODEL_CODES
from ..domain.common import _ULCABaseInferenceRequest
from ..gateway import InferenceGateway
from ..repository import ServiceRepository, ModelRepository
import numpy as np
from ..util import pad_batch, get_string_tensor
import tritonclient.http as http_client
from scipy.io.wavfile import write as scipy_wav_write
import io


class InferenceService:
    def __init__(
        self,
        service_repository: ServiceRepository = Depends(ServiceRepository),
        model_repository: ModelRepository = Depends(ModelRepository),
        inference_gateway: InferenceGateway = Depends(InferenceGateway),
    ) -> None:
        self.service_repository = service_repository
        self.model_repository = model_repository
        self.inference_gateway = inference_gateway

    def run_inference(self, request: _ULCABaseInferenceRequest) -> dict:
        try:
            service = self.service_repository.find_by_id(request.serviceId)
        except:
            raise BaseError(Errors.DHRUVA104.value, traceback.format_exc())

        try:
            model = self.model_repository.find_by_id(service.modelId)
        except:
            raise BaseError(Errors.DHRUVA105.value, traceback.format_exc())

        task_type = model.task.type
        request_body = request.dict()

        if task_type == "translation":
            # Temporary patch for NMT: Since the deployment hosts multiple models, it requires `modelId` explicitly
            self._add_model_id_to_request(request_body)

        return self.inference_gateway.send_inference_request(request_body, service)

    async def run_asr_triton_inference(self, request_body: ULCAAsrInferenceRequest):
        for input in request_body.audio:
            raw_audio = np.array(input.audioContent)
            o = pad_batch(raw_audio)
            input0 = http_client.InferInput("AUDIO_SIGNAL", o[0].shape, "FP32")
            input1 = http_client.InferInput("NUM_SAMPLES", o[1].shape, "INT32")
            input0.set_data_from_numpy(o[0])
            input1.set_data_from_numpy(o[1].astype("int32"))
            output0 = http_client.InferRequestedOutput("TRANSCRIPTS")
            res = {"config": request_body.config, "output": []}
            service = self.service_repository.find_by_id(request_body.serviceId)
            headers = {"Authorization": "Bearer " + service.key}
            response = await self.inference_gateway.send_triton_request(
                url=service.endpoint,
                model_name="offline_conformer",
                input_list=[input0, input1],
                output_list=[output0],
                headers=headers,
            )
            encoded_result = response.as_numpy("TRANSCRIPTS")
            outputs = [result.decode("utf-8") for result in encoded_result.tolist()]
            for output in outputs:
                res["output"].append({"source": output})
        return res

    async def run_translation_triton_inference(self, request_body: ULCATranslationInferenceRequest):
        results = []
        for input in request_body.input:
            input_string = input.source
            inputs = [
                get_string_tensor(input_string, "INPUT_TEXT"),
                get_string_tensor(request_body.config.language.sourceLanguage, "INPUT_LANGUAGE_ID"),
                get_string_tensor(request_body.config.language.targetLanguage, "OUTPUT_LANGUAGE_ID"),
            ]
            output0 = http_client.InferRequestedOutput("OUTPUT_TEXT")
            service = self.service_repository.find_by_id(request_body.serviceId)
            headers = {"Authorization": "Bearer " + service.key}
            response = await self.inference_gateway.send_triton_request(
                url=service.endpoint, model_name="nmt", input_list=inputs, output_list=[output0], headers=headers
            )
            encoded_result = response.as_numpy("OUTPUT_TEXT")
            result = encoded_result.tolist()[0].decode("utf-8")
            results.append({"source": result, "target": input_string})
        res = {"config": request_body.config, "output": results}
        return res

    async def run_tts_triton_inference(self, request_body: ULCATtsInferenceRequest):
        results = []
        for input in request_body.input:
            input_string = input.source
            ip_language = request_body.config.language.sourceLanguage
            ip_gender = request_body.config.gender
            inputs = [
                get_string_tensor(input_string, "INPUT_TEXT"),
                get_string_tensor(ip_gender, "INPUT_SPEAKER_GENDER"),
                get_string_tensor(ip_language, "INPUT_LANGUAGE_ID"),
            ]
            output0 = http_client.InferRequestedOutput("OUTPUT_GENERATED_AUDIO")
            service = self.service_repository.find_by_id(request_body.serviceId)
            headers = {"Authorization": "Bearer " + service.key}
            response = await self.inference_gateway.send_triton_request(
                url=service.endpoint, model_name="tts", input_list=inputs, output_list=[output0], headers=headers
            )
            wav = response.as_numpy("OUTPUT_GENERATED_AUDIO")[0]
            byte_io = io.BytesIO()
            scipy_wav_write(byte_io, 22050, wav)
            results.append({"source": byte_io, "target": input_string})
        res = {"config": request_body.config, "output": results}
        return res

    def _add_model_id_to_request(self, request_body: dict) -> None:
        lang_pair = request_body["config"]["language"]
        lang_pair = lang_pair["sourceLanguage"] + "-" + lang_pair["targetLanguage"]

        request_body["config"]["modelId"] = LANG_TRANS_MODEL_CODES.get(lang_pair, DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID)
