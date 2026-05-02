import axios from "axios";

const client = axios.create({ baseURL: "/api" });

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const serverMessage =
      error.response?.data?.error || error.response?.data?.detail;
    const msg = serverMessage || error.message || "请求失败";
    return Promise.reject(new Error(msg));
  },
);

export default client;
