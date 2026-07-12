// frontend/src/lib/api.js
import axios from "axios";

// Create an Axios instance pointing to your FastAPI backend
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api", // Updated to match running backend
});

// Add a request interceptor to attach the JWT token
api.interceptors.request.use(
  (config) => {
    // Get the token from local storage
    const token = localStorage.getItem("access_token");
    
    // DEBUG: Ensure token is attaching!
    console.log("🛠️ Frontend API Interceptor: attaching token length =", token ? token.length : 0);

    // If the token exists, attach it to the Authorization header
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Add a response interceptor to catch and log errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("🚨 API Error interceptor caught:", error.response?.status, error.response?.data, error.message);
    return Promise.reject(error);
  }
);

export default api;
