// 本地存储工具函数

// Token相关
export const getToken = (): string | null => {
  return localStorage.getItem('token');
};

export const setToken = (token: string): void => {
  localStorage.setItem('token', token);
};

export const removeToken = (): void => {
  localStorage.removeItem('token');
};

// 用户信息相关
export const getUserInfo = (): any | null => {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
};

export const setUserInfo = (user: any): void => {
  localStorage.setItem('user', JSON.stringify(user));
};

export const removeUserInfo = (): void => {
  localStorage.removeItem('user');
};

// 清除所有认证信息
export const clearAuthInfo = (): void => {
  removeToken();
  removeUserInfo();
};
