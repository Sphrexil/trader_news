import axios from "axios";
import toast from "react-hot-toast";

export class ApiError extends Error {
  constructor(
    public code: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 10000,
});

client.interceptors.response.use(
  (response) => {
    const res = response.data;
    if (res.code !== 0) {
      toast.error(res.message || "请求失败");
      return Promise.reject(new ApiError(res.code, res.message));
    }
    return res.data;
  },
  (error) => {
    const msg = error.response?.data?.message || error.message || "网络错误";
    if (error.response?.status !== 404 && error.response?.status !== 422) {
      toast.error(msg);
    }
    return Promise.reject(new Error(msg));
  },
);

export default client;
