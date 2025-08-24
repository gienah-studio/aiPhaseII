import request from '../common/request';
import type { BonusPoolSummary, DailySubsidyStats, DailySubsidyStatsParams } from './types';

/**
 * 获取奖金池汇总信息
 */
export const getBonusPoolSummary = async (poolDate?: string): Promise<BonusPoolSummary> => {
  const response = await request.get<BonusPoolSummary>('/bonusPool/summary', {
    params: poolDate ? { pool_date: poolDate } : undefined
  });
  return response.data;
};

/**
 * 获取每日补贴统计数据
 */
export const getDailySubsidyStats = async (params?: DailySubsidyStatsParams): Promise<DailySubsidyStats> => {
  const response = await request.get<DailySubsidyStats>('/bonusPool/dailyStats', {
    params
  });
  return response.data;
};

/**
 * 导出每日补贴统计数据
 */
export const exportDailySubsidyStats = async (params?: DailySubsidyStatsParams): Promise<Blob> => {
  try {
    const response = await request.get('/bonusPool/dailyStats/export', {
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
    console.error('导出每日补贴统计数据失败:', error);
    throw error;
  }
};

export * from './types';