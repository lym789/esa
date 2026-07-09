export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CurrentUser = {
  id: number;
  email: string;
  name: string;
  role: "employee" | "handler" | "approver" | "admin";
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: CurrentUser;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = response.status === 401 ? "邮箱或密码不正确" : "请求失败，请稍后重试";
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  return parseResponse<LoginResponse>(response);
}

export async function getMe(accessToken: string): Promise<CurrentUser> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    cache: "no-store",
  });

  return parseResponse<CurrentUser>(response);
}
