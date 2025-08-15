import request from '../common/request';
import type {
  VirtualOrderStats,
  StudentPoolListResponse,
  StudentPoolParams,
  VirtualCustomerServiceListResponse,
  VirtualCustomerServiceParams,
  VirtualCustomerServiceCreate,
  VirtualCustomerServiceUpdate,
  VirtualCustomerServiceResponse,
  VirtualCustomerServiceUpdateResponse,
  VirtualCustomerServiceDeleteResponse,
  StudentIncomeSummaryResponse,
  StudentIncomeSummaryParams,
  ReallocateTasksResponse,
  CustomerServiceImportResponse,
  StudentSubsidyImportResponse
} from './types';
import type { ApiResponse } from '../common/types';

/**
 * 获取虚拟订单统计信息
 */
export const getVirtualOrderStats = async (): Promise<VirtualOrderStats> => {
  const response = await request.get<ApiResponse<VirtualOrderStats>>('/virtualOrders/stats');
  return response.data;
};

/**
 * 获取学生补贴池列表
 */
export const getStudentPools = async (params?: StudentPoolParams): Promise<StudentPoolListResponse> => {
  const response = await request.get<ApiResponse<StudentPoolListResponse>>('/virtualOrders/studentPools', {
    params
  });
  return response.data;
};

// ==================== 专属客服相关API ====================

/**
 * 获取虚拟客服列表
 */
export const getVirtualCustomerServices = async (params?: VirtualCustomerServiceParams): Promise<VirtualCustomerServiceListResponse> => {
  const response = await request.get<ApiResponse<VirtualCustomerServiceListResponse>>('/virtualOrders/customerService', {
    params
  });
  return response.data;
};

/**
 * 创建虚拟客服
 */
export const createVirtualCustomerService = async (data: VirtualCustomerServiceCreate): Promise<VirtualCustomerServiceResponse> => {
  const response = await request.post<ApiResponse<VirtualCustomerServiceResponse>>('/virtualOrders/customerService', data);
  return response.data;
};

/**
 * 更新虚拟客服信息
 */
export const updateVirtualCustomerService = async (roleId: number, data: VirtualCustomerServiceUpdate): Promise<VirtualCustomerServiceUpdateResponse> => {
  const response = await request.put<ApiResponse<VirtualCustomerServiceUpdateResponse>>(`/virtualOrders/customerService/${roleId}`, data);
  return response.data;
};

/**
 * 删除虚拟客服
 */
export const deleteVirtualCustomerService = async (roleId: number): Promise<VirtualCustomerServiceDeleteResponse> => {
  const response = await request.delete<ApiResponse<VirtualCustomerServiceDeleteResponse>>(`/virtualOrders/customerService/${roleId}`);
  return response.data;
};

/**
 * 导入专用客服
 */
export const importCustomerService = async (file: File): Promise<CustomerServiceImportResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await request.post<ApiResponse<CustomerServiceImportResponse>>('/virtualOrders/import/customerService', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// ==================== 学生收入相关API ====================

/**
 * 获取学生收入汇总
 */
export const getStudentIncomeSummary = async (params?: StudentIncomeSummaryParams): Promise<StudentIncomeSummaryResponse> => {
  const response = await request.get<ApiResponse<StudentIncomeSummaryResponse>>('/virtualOrders/studentIncome/summary', {
    params
  });
  return response.data;
};

/**
 * 重新分配学生任务
 */
export const reallocateStudentTasks = async (studentId: number): Promise<ReallocateTasksResponse> => {
  const response = await request.post<ApiResponse<ReallocateTasksResponse>>(`/virtualOrders/reallocate/${studentId}`);
  return response.data;
};

/**
 * 删除学生补贴池
 */
export const deleteStudentPool = async (poolId: number): Promise<{ deleted: boolean; message: string }> => {
  const response = await request.delete<ApiResponse<{ deleted: boolean; message: string }>>(`/virtualOrders/studentPools/${poolId}`);
  return response.data;
};

/**
 * 导出学生收入数据
 */
export const exportStudentIncome = async (params?: StudentIncomeSummaryParams & { student_ids?: number[] }): Promise<Blob> => {
  try {
    const response = await request.get('/virtualOrders/studentIncome/export', {
      params,
      responseType: 'blob'
    });

    // 由于我们修改了响应拦截器，对于 Blob 类型直接返回 response.data
    // 但这里我们需要确保返回的是 Blob 对象
    if (response instanceof Blob) {
      return response;
    } else if (response.data instanceof Blob) {
      return response.data;
    } else {
      // 如果不是 Blob，可能是错误响应，抛出错误
      throw new Error('服务器返回的不是文件数据');
    }
  } catch (error) {
    console.error('导出学生收入数据失败:', error);
    throw error;
  }
};

/**
 * 导入学生补贴
 */
export const importStudentSubsidy = async (file: File): Promise<StudentSubsidyImportResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await request.post<ApiResponse<StudentSubsidyImportResponse>>('/virtualOrders/import/studentSubsidy', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export * from './types';
