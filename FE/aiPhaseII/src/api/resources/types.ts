// 资源相关类型定义

export interface Resource {
  id: string;
  fileName: string;
  originalName: string;
  filePath: string;
  thumbnailPath?: string;
  fileSize: number;
  fileSizeFormatted: string;
  mimeType: string;
  dimensions?: {
    width: number;
    height: number;
  };
  dimensionsFormatted?: string;
  categoryId: string;
  categoryName: string;
  qualityScore: number;
  status: 'available' | 'used' | 'disabled';
  tags: string[];
  description?: string;
  uploadBatchId?: string;
  uploadedBy: string;
  uploadedAt: string;
  updatedAt: string;
  downloadCount: number;
  usageCount: number;
}

export interface ResourceCategory {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  resourceCount: number;
  children?: ResourceCategory[];
  icon?: string;
  color?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ResourceUploadBatch {
  id: string;
  name: string;
  description?: string;
  totalCount: number;
  successCount: number;
  failedCount: number;
  status: 'uploading' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
}

// 查询参数类型
export interface ResourceQueryParams {
  page?: number;
  pageSize?: number;
  keyword?: string;
  categoryId?: string;
  status?: Resource['status'];
  tags?: string[];
  qualityRangeMin?: number;
  qualityRangeMax?: number;
  fileSizeMin?: number;
  fileSizeMax?: number;
  uploadBatchId?: string;
  uploadedBy?: string;
  startDate?: string;
  endDate?: string;
  sortBy?: 'uploadedAt' | 'fileName' | 'fileSize' | 'qualityScore' | 'downloadCount';
  sortOrder?: 'asc' | 'desc';
}

// 资源统计类型
export interface ResourceStats {
  totalCount?: number;
  categoryCount?: number;
  todayUploadCount?: number;
  totalSize?: number;
  totalSizeFormatted?: string;
  // 新增字段以适配后端API
  totalImages?: number;
  availableImages?: number;
  usedImages?: number;
  categoriesStats?: Array<{
    category_name: string;
    total: number;
  }>;
  statusDistribution?: {
    available: number;
    used: number;
    disabled: number;
  };
  topCategories?: Array<{
    categoryId: string;
    categoryName: string;
    count: number;
  }>;
  topTags?: Array<{
    tag: string;
    count: number;
  }>;
}

// 上传相关类型
export interface UploadResourceData {
  categoryId: string;
  qualityScore: number;
  tags: string[];
  description?: string;
}

export interface BatchUploadData extends UploadResourceData {
  batchName?: string;
  batchDescription?: string;
}

export interface UploadProgress {
  id: string;
  fileName: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

// 批量操作类型
export interface BatchOperationParams {
  resourceIds: string[];
  operation: 'delete' | 'move' | 'updateStatus' | 'addTags' | 'removeTags';
  params?: {
    targetCategoryId?: string;
    status?: Resource['status'];
    tags?: string[];
  };
}

// 分类操作类型
export interface CreateCategoryData {
  name: string;
  description?: string;
  parentId?: string;
  color?: string;
}

export interface UpdateCategoryData {
  name?: string;
  description?: string;
  parentId?: string;
  color?: string;
}

// API 响应类型
export interface ApiResponse<T = any> {
  code: number;
  msg: string;
  data: T;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ResourceListResponse extends PaginationResponse<Resource> {}

export interface CategoryListResponse {
  categories: ResourceCategory[];
  total: number;
}

// 批量删除请求类型
export interface BatchDeleteRequest {
  imageIds: string[];
}

// 批量移动分类请求类型
export interface BatchMoveCategoryRequest {
  imageIds: string[];
  targetCategoryId: string;
}

// 批量操作响应类型
// 批量删除响应
export interface BatchDeleteResponse {
  totalRequested: number;
  deletedCount: number;
  skippedCount: number;
  deleteReason?: string;
}

// 批量移动分类响应
export interface BatchMoveCategoryResponse {
  totalRequested: number;
  movedCount: number;
  skippedCount: number;
  targetCategory: {
    id: number;
    name: string;
  };
  moveReason?: string;
}

// 通用批量操作响应（保持向后兼容）
export interface BatchOperationResponse {
  success: boolean;
  message: string;
  affected: number;
  errors?: Array<{
    imageId: string;
    error: string;
  }>;
}

// 分类详细统计类型
export interface CategoryDetailedStats {
  total: number;
  available: number;
  used: number;
  rate: number; // 使用率
}

// 详细统计响应类型
export interface DetailedStatsResponse {
  avatarRedesign: CategoryDetailedStats; // 头像改版
  roomDecoration: CategoryDetailedStats; // 装修风格  
  photoExtension: CategoryDetailedStats; // 照片扩图
}

// 错误类型
export interface ApiError {
  code: number;
  message: string;
  details?: any;
}