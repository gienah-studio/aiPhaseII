import request from '../common/request';
import type {
  Resource,
  ResourceCategory,
  ResourceQueryParams,
  ResourceStats,
  UploadResourceData,
  BatchUploadData,
  BatchOperationParams,
  CreateCategoryData,
  UpdateCategoryData,
  ApiResponse,
  ResourceListResponse,
  CategoryListResponse,
  BatchDeleteRequest,
  BatchMoveCategoryRequest,
  BatchDeleteResponse,
  BatchMoveCategoryResponse,
  DetailedStatsResponse
} from './types';

// 资源管理API
class ResourceAPI {
  // 获取资源列表
  static async getResources(params?: ResourceQueryParams): Promise<ApiResponse<ResourceListResponse>> {
    // 映射前端参数名到后端期望的参数名
    const mappedParams = params ? {
      page: params.page,
      size: params.pageSize,
      category_id: params.categoryId,
      status: params.status,
      search_keyword: params.keyword,
      start_date: params.startDate,
      end_date: params.endDate
    } : undefined;
    
    return request.get('/resources', { params: mappedParams });
  }

  // 获取资源详情
  static async getResourceById(id: string): Promise<ApiResponse<Resource>> {
    return request.get(`/resources/${id}`);
  }

  // 上传单个资源文件
  static async uploadResource(file: File, data: UploadResourceData): Promise<ApiResponse<Resource>> {
    const formData = new FormData();
    formData.append('files', file);
    formData.append('categoryId', data.categoryId);
    formData.append('description', data.description || '');
    // 暂时不发送其他参数，因为后端接口比较简单

    return request.post('/resources/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // 批量上传压缩包
  static async uploadArchive(file: File, data: BatchUploadData): Promise<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('files', file);
    formData.append('categoryId', data.categoryId);
    formData.append('description', data.description || '');

    return request.post('/resources/upload', formData, {  // 使用同一个接口
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // 更新资源信息
  static async updateResource(id: string, data: Partial<Resource>): Promise<ApiResponse<Resource>> {
    return request.put(`/resources/${id}`, data);
  }

  // 删除资源
  static async deleteResource(id: string): Promise<ApiResponse<null>> {
    return request.delete(`/resources/images/${id}`);
  }

  // 下载资源文件
  static async downloadResource(id: string): Promise<Blob> {
    return request.get(`/resources/${id}/download`, {
      responseType: 'blob',
    });
  }

  // 批量下载资源
  static async downloadResources(ids: string[]): Promise<Blob> {
    return request.post('/resources/download-batch', { ids }, {
      responseType: 'blob',
    });
  }

  // 获取资源统计数据
  static async getResourceStats(): Promise<ApiResponse<ResourceStats>> {
    return request.get('/resources/stats');
  }

  // 获取分类详细统计数据
  static async getCategoryDetailedStats(): Promise<ApiResponse<DetailedStatsResponse>> {
    return request.get('/resources/category-stats');
  }

  // 批量操作
  static async batchOperation(params: BatchOperationParams): Promise<ApiResponse<any>> {
    return request.post('/resources/batch-operation', params);
  }

  // 搜索资源
  static async searchResources(query: string, filters?: Partial<ResourceQueryParams>): Promise<ApiResponse<ResourceListResponse>> {
    return request.get('/resources/search', {
      params: { query, ...filters }
    });
  }

  // 批量删除资源
  static async batchDeleteResources(imageIds: string[]): Promise<ApiResponse<BatchDeleteResponse>> {
    const data: BatchDeleteRequest = { imageIds };
    return request.post('/resources/images/batch-delete', data);
  }

  // 批量移动分类
  static async batchMoveCategoryResources(imageIds: string[], targetCategoryId: string): Promise<ApiResponse<BatchMoveCategoryResponse>> {
    const data: BatchMoveCategoryRequest = { imageIds, targetCategoryId };
    return request.post('/resources/images/batch-move-category', data);
  }
}

// 分类管理API
class CategoryAPI {
  // 获取分类列表
  static async getCategories(): Promise<ApiResponse<CategoryListResponse>> {
    return request.get('/resources/categories');
  }

  // 获取分类详情
  static async getCategoryById(id: string): Promise<ApiResponse<ResourceCategory>> {
    return request.get(`/resources/categories/${id}`);
  }

  // 创建分类
  static async createCategory(data: CreateCategoryData): Promise<ApiResponse<ResourceCategory>> {
    return request.post('/resources/categories', data);
  }

  // 更新分类
  static async updateCategory(id: string, data: UpdateCategoryData): Promise<ApiResponse<ResourceCategory>> {
    return request.put(`/resources/categories/${id}`, data);
  }

  // 删除分类
  static async deleteCategory(id: string): Promise<ApiResponse<null>> {
    return request.delete(`/resources/categories/${id}`);
  }

  // 移动分类
  static async moveCategory(id: string, parentId?: string): Promise<ApiResponse<ResourceCategory>> {
    return request.post(`/resources/categories/${id}/move`, { parentId });
  }

  // 获取分类资源数量
  static async getCategoryResourceCount(id: string): Promise<ApiResponse<{ count: number }>> {
    return request.get(`/resources/categories/${id}/count`);
  }
}

// 标签管理API
class TagAPI {
  // 获取所有标签
  static async getTags(): Promise<ApiResponse<Array<{ tag: string; count: number }>>> {
    return request.get('/resources/tags');
  }

  // 搜索标签
  static async searchTags(query: string): Promise<ApiResponse<string[]>> {
    return request.get('/resources/tags/search', { params: { query } });
  }

  // 获取热门标签
  static async getPopularTags(limit = 20): Promise<ApiResponse<Array<{ tag: string; count: number }>>> {
    return request.get('/resources/tags/popular', { params: { limit } });
  }

  // 创建标签
  static async createTag(tag: string): Promise<ApiResponse<{ tag: string }>> {
    return request.post('/resources/tags', { tag });
  }

  // 删除标签
  static async deleteTag(tag: string): Promise<ApiResponse<null>> {
    return request.delete(`/resources/tags/${encodeURIComponent(tag)}`);
  }
}

// 导出默认的资源API
export default ResourceAPI;

// 导出其他API
export { CategoryAPI, TagAPI };

// 导出类型
export type * from './types';