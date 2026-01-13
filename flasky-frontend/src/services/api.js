import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:3000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // For session cookies
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh and extract data from unified response
api.interceptors.response.use(
  (response) => {
    // Extract data from unified response structure
    if (response.data && response.data.success !== undefined) {
      return {
        ...response,
        data: response.data.data,
        meta: response.data.meta,
        message: response.data.message,
        success: response.data.success,
        _raw: response.data, // Keep raw response if needed
      };
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          if (response.data.success) {
            const { access_token } = response.data.data;
            localStorage.setItem("access_token", access_token);

            // Retry original request
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, logout user
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
      }
    }

    // Extract error message from unified response
    const errorMessage =
      error.response?.data?.message ||
      error.response?.data?.errors ||
      error.message ||
      "An error occurred";

    return Promise.reject({
      ...error,
      message: errorMessage,
      errors: error.response?.data?.errors,
      errorCode: error.response?.data?.error_code,
    });
  }
);

// Authentication APIs
export const authApi = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  logout: (refreshToken) =>
    api.post("/auth/logout", { refresh_token: refreshToken }),
  getProfile: () => api.get("/auth/profile"),
  updateProfile: (data) => api.put("/auth/profile", data),
  verifyEmail: (token) => api.post("/auth/verify-email", { token }),
  resendVerification: (email) =>
    api.post("/auth/resend-verification", { email }),
  forgotPassword: (email) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token, newPassword) =>
    api.post("/auth/reset-password", { token, new_password: newPassword }),
  changePassword: (currentPassword, newPassword) =>
    api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  refresh: (refreshToken) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }),
};

// Products APIs
export const productsApi = {
  getAll: (params = {}) => api.get("/products", { params }),
  create: (product) => api.post("/products", product),
};

// Orders APIs
export const ordersApi = {
  getAll: (params = {}) => api.get("/orders", { params }),
  create: (order) => api.post("/orders", order),
  getById: (id) => api.get(`/orders/${id}`),
  addItem: (orderId, item) => api.post(`/orders/${orderId}/items`, item),
  pay: (orderId) => api.post(`/orders/${orderId}/pay`),
};

export default api;
