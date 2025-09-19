import axios from "axios";

const API_BASE_URL = "http://localhost:3000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const productsApi = {
  getAll: () => api.get("/products"),
  create: (product) => api.post("/products", product),
};

export const ordersApi = {
  getAll: () => api.get("/orders"),
  create: (order) => api.post("/orders", order),
  getById: (id) => api.get(`/orders/${id}`),
  addItem: (orderId, item) => api.post(`/orders/${orderId}/items`, item),
  pay: (orderId) => api.post(`/orders/${orderId}/pay`),
};

export default api;
