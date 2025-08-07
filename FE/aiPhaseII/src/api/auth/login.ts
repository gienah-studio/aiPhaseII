import request from '../common/request';
import type { AuthResponse, LoginRequest, AllStudentsIncomeStatsResponse } from './types';
import type { ApiResponse } from '../common/types';

// 登录接口
export const login = (data: LoginRequest): Promise<AuthResponse> => {
  return request.post('/auth/login', data);
};

// 获取所有学员每日收入统计
export const getAllStudentsDailyIncomeStats = (params?: {
  page?: number;
  size?: number;
}): Promise<ApiResponse<AllStudentsIncomeStatsResponse>> => {
  return request.get('/auth/student/daily-income-stats', { params });
};
