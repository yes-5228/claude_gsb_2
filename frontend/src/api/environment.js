import { http } from './client.js';

const RESOURCE = '/environment-records';

export const environmentApi = {
  list: (params) => http.get(RESOURCE, params),
  trend: (restroomId) => http.get(`${RESOURCE}/trend`, { restroom_id: restroomId }),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
};
