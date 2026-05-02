import { message as antMessage } from "antd";
import axios from "axios";

const client = axios.create({ baseURL: "/api" });

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const serverMessage = error.response?.data?.message || error.response?.data?.detail;
    const msg = serverMessage || error.message || "请求失败";
    if (!error.config?._silent) {
      antMessage.error(msg);
    }
    return Promise.reject(new Error(msg));
  },
);

export default client;
