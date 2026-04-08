import { api } from "./client";

export interface MeResponse {
  username: string;
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ message: string }>("/auth/login", { username, password }),

  logout: () => api.post<{ message: string }>("/auth/logout"),

  me: () => api.get<MeResponse>("/auth/me"),
};
