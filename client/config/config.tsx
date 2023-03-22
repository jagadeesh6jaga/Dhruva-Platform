import { createContext } from "react";
import axios, { AxiosHeaders, AxiosRequestConfig } from "axios";

const dhruvaRootURL: string = process.env.NEXT_PUBLIC_BACKEND_API_URL;

const dhruvaConfig: { [key: string]: string } = {
  listServices: `${dhruvaRootURL}/services/details/list_services`,
  viewService: `${dhruvaRootURL}/services/details/view_service`,
  listModels: `${dhruvaRootURL}/services/details/list_models`,
  viewModel: `${dhruvaRootURL}/services/details/view_model`,
  genericInference: `${dhruvaRootURL}/services/inference`,
  translationInference: `${dhruvaRootURL}/services/inference/translation`,
  ttsInference: `${dhruvaRootURL}/services/inference/tts`,
  asrInference: `${dhruvaRootURL}/services/inference/asr`,
  asrStreamingInference: `wss://api.dhruva.ai4bharat.org`,
  stsInference: `${dhruvaRootURL}/services/inference/s2s`,
  nerInference: `${dhruvaRootURL}/services/inference/ner`,
};

const lang2label: { [key: string]: string } = {
  as : "Assamese",
  awa: "Awadhi",
  bho: "Bhojpuri",
  bn : "Bangla",
  brx: "Boro",
  doi: "Dogri",
  en : "English",
  gom: "Goan-Konkani",
  gu : "Gujarati",
  hi : "Hindi",
  hne: "Hindi-Eastern (Chhattisgarhi)",
  kn : "Kannada",
  ks : "Kashmiri",
  ks_Deva: "Kashmiri (Devanagari)",
  kha: "Khasi",
  lus: "Lushai (Mizo)",
  mag: "Magahi",
  mai: "Maithili",
  ml : "Malayalam",
  mni: "Manipuri",
  mni_Beng: "Manipuri (Bengali)",
  mr : "Marathi",
  ne : "Nepali",
  or : "Oriya",
  pa : "Panjabi",
  raj: "Rajasthani",
  sa : "Sanskrit",
  sat: "Santali",
  sd : "Sindhi",
  sd_Deva: "Sindhi (Devanagari)",
  si : "Sinhala",
  ta : "Tamil",
  te : "Telugu",
  ur : "Urdu",
};

const tag2Color = {
  "B-LOC": ["#ffcccc", "#ff0000"],
  "B-ORG": ["#cceeff", "#00aaff"],
  "B-PER": ["#d6f5d6", "#33cc33"],
  "I-LOC": ["#ffccdd", "#ff0055"],
  "I-ORG": ["#ffffcc", "#ffff00"],
  "I-PER": ["#e6ccff", "#8000ff"],
  O: ["#ffe6cc", "#ff8000"],
};

const apiInstance = axios.create();

apiInstance.interceptors.request.use((config: any) => {
    
  config.headers["request-startTime"] = new Date().getTime();
  return config;
});

apiInstance.interceptors.response.use((response: any) => {
  const currentTime = new Date().getTime();
  const startTime = response.config.headers["request-startTime"];
  response.headers["request-duration"] = currentTime - startTime;
  return response;
});

export { dhruvaConfig, lang2label, apiInstance, tag2Color };
