import axios from 'axios';
import { clearAuthInfo } from '../../utils/storage';
import { ROUTES } from '../../constants/routes';
import type { ApiError } from './types';

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  // timeout: 10000, // 移除超时限制，允许长时间上传
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 对于文件下载请求，不设置 Content-Type
    if (config.responseType === 'blob') {
      delete config.headers['Content-Type'];
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const data = response.data;

    // 如果是二进制数据（Blob），直接返回
    if (data instanceof Blob) {
      return data;
    }

    // 检查业务状态码
    if (data.code && data.code !== 200) {
      // 检查是否是token过期（业务状态码401）
      if (data.code === 401) {
        // token过期，清除认证信息并跳转到登录页
        clearAuthInfo();
        window.location.href = ROUTES.LOGIN;
        return Promise.reject(new Error(data.message || '登录已过期，请重新登录'));
      }

      // 其他业务失败，创建一个错误对象
      const error = new Error(data.message || '请求失败') as ApiError;
      error.apiResponse = data;
      error.businessError = true;
      return Promise.reject(error);
    }

    return data;
  },
  (error) => {
    // 处理HTTP错误响应
    if (error.response?.status === 401) {
      // HTTP 401未授权，清除认证信息并跳转到登录页
      clearAuthInfo();
      window.location.href = ROUTES.LOGIN;
    }

    // 如果有响应数据，将错误信息附加到error对象上，方便前端处理
    if (error.response?.data) {
      error.apiResponse = error.response.data;
      // 优先使用detail字段，然后是message字段
      error.message = error.response.data.detail || error.response.data.message || error.message;
    }

    return Promise.reject(error);
  }
);

export default request;
