import { dhruvaAPI, apiInstance } from "./apiConfig";

interface LanguageConfig {
  sourceLanguage: string;
  targetLanguage: string;
}

interface IFeedback {
  language: LanguageConfig;
  example: string;
  rating: number;
  comments: string;
  service_id: string;
}

const listServices = async (): Promise<ServiceList[]> => {
  const response = await apiInstance({
    method: "GET",
    url: dhruvaAPI.listServices,
  });
  return response.data;
};

const listallkeys = async (target_service_id: string) => {
  const response = await apiInstance.get(
    `/auth/api-key/list?target_service_id=${target_service_id}`
  );
  return response.data;
};

const listalluserkeys = async (target_service_id: string, user_id: string) => {
  const response = await apiInstance.get(
    `/auth/api-key/list?target_user_id=${user_id}&target_service_id=${target_service_id}`
  );
  return response.data;
};

const getService = async (
  serviceId: string | string[]
): Promise<ServiceView> => {
  const response = await apiInstance({
    method: "POST",
    url: dhruvaAPI.viewService,
    data: {
      serviceId: serviceId,
    },
  });
  return response.data;
};

const submitFeedback = async (feedback: IFeedback) => {
  const response = await apiInstance.post(
    `/services/feedback/submit`,
    feedback
  );
  return response.data;
};

export {
  listServices,
  getService,
  submitFeedback,
  listallkeys,
  listalluserkeys,
};
