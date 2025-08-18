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
  StudentSubsidyImportResponse,
  VirtualTaskGenerationConfig,
  UpdateVirtualTaskGenerationConfigParams
} from './types';
import type { ApiResponse } from '../common/types';

/**
 * 获取虚拟订单统计信息
 */
export const getVirtualOrderStats = async (): Promise<any> => {
  const response = await request.get<any>('/virtualOrders/stats');
  return response.data;
};

/**
 * 获取学生补贴池列表
 */
export const getStudentPools = async (params?: StudentPoolParams): Promise<any> => {
  const response = await request.get<any>('/virtualOrders/studentPools', {
    params
  });
  return response.data;
};

// ==================== 专属客服相关API ====================

/**
 * 获取虚拟客服列表
 */
export const getVirtualCustomerServices = async (params?: VirtualCustomerServiceParams): Promise<any> => {
  const response = await request.get<any>('/virtualOrders/customerService', {
    params
  });
  return response.data;
};

/**
 * 创建虚拟客服
 */
export const createVirtualCustomerService = async (data: VirtualCustomerServiceCreate): Promise<any> => {
  const response = await request.post<any>('/virtualOrders/customerService', data);
  return response.data;
};

/**
 * 更新虚拟客服信息
 */
export const updateVirtualCustomerService = async (csId: number, data: VirtualCustomerServiceUpdate): Promise<any> => {
  const response = await request.put<any>(`/virtualOrders/customerService/${csId}`, data);
  return response.data;
};

/**
 * 删除虚拟客服
 */
export const deleteVirtualCustomerService = async (csId: number): Promise<any> => {
  const response = await request.delete<any>(`/virtualOrders/customerService/${csId}`);
  return response.data;
};

/**
 * 导入专用客服
 */
export const importCustomerService = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await request.post<any>('/virtualOrders/import/customerService', formData, {
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
export const getStudentIncomeSummary = async (params?: StudentIncomeSummaryParams): Promise<any> => {
  const response = await request.get<any>('/virtualOrders/studentIncome/summary', {
    params
  });
  return response.data;
};

/**
 * 重新分配学生任务
 */
export const reallocateStudentTasks = async (studentId: number): Promise<any> => {
  const response = await request.post<any>(`/virtualOrders/reallocate/${studentId}`);
  return response.data;
};

/**
 * 删除学生补贴池
 */
export const deleteStudentPool = async (poolId: number): Promise<any> => {
  const response = await request.delete<any>(`/virtualOrders/studentPools/${poolId}`);
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
export const importStudentSubsidy = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await request.post<any>('/virtualOrders/import/studentSubsidy', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// ==================== 虚拟任务生成配置相关API ====================

/**
 * 获取虚拟任务生成配置
 */
export const getVirtualTaskGenerationConfig = async (): Promise<any> => {
  const response = await request.get<any>('/virtualOrders/virtualTaskGenerationConfig');
  return response.data;
};

/**
 * 更新虚拟任务生成配置
 */
export const updateVirtualTaskGenerationConfig = async (params: UpdateVirtualTaskGenerationConfigParams): Promise<any> => {
  const response = await request.post<any>('/virtualOrders/virtualTaskGenerationConfig', null, {
    params
  });
  return response.data;
};

export * from './types';
