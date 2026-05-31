import { api, retryRequest, isNetworkError, isColdStartError } from './api';
import type { MeUserResponse, RegisterPayload, RegisterResponse } from '../types';

export const authApi = {
  register: async (payload: RegisterPayload): Promise<RegisterResponse> => {
    const response = await api.post<RegisterResponse>('/register', payload);
    return response.data;
  },

  login: async (email: string, password: string) => {
    // Debug: Log request payload (only in development)
    if (import.meta.env.DEV) {
      console.log('[authApi.login] Request payload:', { username: email, password: '***' });
    }

    // Send as x-www-form-urlencoded for OAuth2PasswordRequestForm compatibility.
    // The backend uses FastAPI's OAuth2PasswordRequestForm which expects `username` + `password`.
    const formData = new URLSearchParams();
    formData.append('username', email);  // OAuth2 uses 'username' field
    formData.append('password', password);

    // Use retry logic to handle PaaS cold starts (no response / timeout).
    const response = await retryRequest(
      () =>
        api.post('/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }),
      3, // 3 retries
      2500 // 2.5s delay between retries
    );

    // Debug: Log response (only in development)
    if (import.meta.env.DEV) {
      console.log('[authApi.login] Response:', response.data);
    }
    return response.data;
  },

  resetPassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    await api.post('/auth/reset-password', {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },

  /** Current user from the database (authoritative role / tenant / owner flags). */
  getMe: async (): Promise<MeUserResponse> => {
    const { data } = await api.get<MeUserResponse>('/me');
    return data;
  },
};

// Helper to format login errors with user-friendly messages
export const formatLoginError = (error: any): string => {
  if (isColdStartError(error)) {
    return 'Server is waking up, please try again in a few seconds...';
  }
  if (isNetworkError(error)) {
    return 'Connection issue. Please check your internet and try again.';
  }
  // Backend returned an error response
  if (error?.detail) {
    return error.detail;
  }
  if (error?.message) {
    return error.message;
  }
  return 'Login failed. Please check your credentials and try again.';
};
