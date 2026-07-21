// frontend/src/lib/api.ts
import axios from "axios";

// Create an Axios instance pointing to your FastAPI backend
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// Add a request interceptor to attach the JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Add a response interceptor to handle auth and log errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;

    // AUTO-LOGOUT on 401 Unauthorized
    // This handles InvalidSignatureError (old tokens signed with old key)
    // and any other expired/invalid token situations.
    if (status === 401) {
      const currentPath = window.location.pathname;
      // Only redirect if not already on a public page (avoid redirect loops)
      const publicPaths = ["/", "/login", "/signup", "/register", "/landing"];
      const isPublicPage = publicPaths.some(p => currentPath === p || currentPath.startsWith(p));
      
      if (!isPublicPage) {
        console.warn("🔐 401 Unauthorized — clearing invalid token and redirecting to login");
        localStorage.removeItem("access_token");
        // Use replace() so the user can't navigate back to the protected page
        window.location.replace("/login");
      } else {
        // On public pages, just remove the bad token silently
        localStorage.removeItem("access_token");
      }
    }

    console.error(
      "🚨 API Error interceptor caught:",
      status,
      error.response?.data,
      error.message
    );
    return Promise.reject(error);
  }
);

export default api;
