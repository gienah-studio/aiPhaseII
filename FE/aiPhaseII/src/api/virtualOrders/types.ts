/**
 * 虚拟订单统计数据类型
 */
export interface VirtualOrderStats {
  totalStudents: number;
  totalSubsidy: number;
  totalTasksGenerated: number;
  totalTasksCompleted: number;
  completionRate: number;
  // 新增奖金池相关字段
  bonusPoolTotal?: number;
  qualifiedStudentsCount?: number;
}

/**
 * 虚拟订单每日统计数据类型
 */
export interface VirtualOrderDailyStats {
  date: string;
  dailyTasksGenerated: number;
  dailyTasksCompleted: number;
  dailySubsidy: number;
  dailyActiveStudents: number;
  dailyCompletionRate: number;
}

/**
 * 学生补贴池项目类型
 */
export interface StudentPoolItem {
  id: number;
  studentId?: number;
  studentName?: string;
  totalSubsidy?: number;
  remainingAmount?: number;
  allocatedAmount?: number;
  completedAmount?: number;
  consumedSubsidy?: number;
  bonusPoolConsumedSubsidy?: number;  // 奖金池任务实际获得的补贴金额
  totalConsumedSubsidy?: number;      // 总消耗补贴金额
  completionRate?: number;
  agentRebate?: string;
  status: string;
  importBatch?: string;
  createdAt?: string;
  lastAllocationAt?: string;
  // 兼容旧字段名
  student_name?: string;
  student_id?: string;
  subsidy_amount?: number;
  remaining_amount?: number;
  tasks_generated?: number;
  tasks_completed?: number;
  completion_rate?: number;
  created_at?: string;
  updated_at?: string;
}

/**
 * 学生补贴池列表响应类型
 */
export interface StudentPoolListResponse {
  items: StudentPoolItem[];
  total: number;
  page: number;
  size: number;
}

/**
 * 学生补贴池查询参数
 */
export interface StudentPoolParams {
  page?: number;
  size?: number;
  status?: string;
}

// ==================== 专属客服相关类型 ====================

/**
 * 虚拟客服信息
 */
export interface VirtualCustomerServiceInfo {
  id: number;
  userId?: number;
  name: string;
  account: string;
  level: string;
  status: string;
  lastLoginTime?: string;
  createdAt?: string;
}

/**
 * 虚拟客服列表响应
 */
export interface VirtualCustomerServiceListResponse {
  items: VirtualCustomerServiceInfo[];
  total: number;
  page: number;
  size: number;
}

/**
 * 虚拟客服查询参数
 * 根据接口文档，只支持分页参数
 */
export interface VirtualCustomerServiceParams {
  page?: number;
  size?: number;
}

/**
 * 创建虚拟客服请求
 * 根据业务需求，虚拟客服只需要姓名、账号和初始密码
 */
export interface VirtualCustomerServiceCreate {
  name: string;
  account: string;
  initialPassword?: string;
}

/**
 * 更新虚拟客服请求
 * 根据业务需求，编辑时可以修改姓名和密码
 */
export interface VirtualCustomerServiceUpdate {
  name?: string;
  newPassword?: string;
}

/**
 * 虚拟客服响应
 */
export interface VirtualCustomerServiceResponse {
  id: number;
  user_id: number;
  name: string;
  account: string;
  level: string;
  status: string;
  initial_password?: string;
}

/**
 * 更新虚拟客服响应
 */
export interface VirtualCustomerServiceUpdateResponse {
  id: number;
  name: string;
  account: string;
  status: string;
  updated_fields: string[];
}

/**
 * 删除虚拟客服响应
 */
export interface VirtualCustomerServiceDeleteResponse {
  id: number;
  name: string;
  account: string;
  deleted: boolean;
}

// ==================== 学生收入相关类型 ====================

/**
 * 学生收入汇总响应
 */
export interface StudentIncomeSummaryResponse {
  totalStudents: number;
  totalTasks: number;
  totalAmount: number;
  completedTasks: number;
  completedAmount: number;
  completionRate: number;
  exportTime: string;
}

/**
 * 学生收入汇总查询参数
 */
export interface StudentIncomeSummaryParams {
  startDate?: string;
  endDate?: string;
}

/**
 * 重新分配学生任务响应
 */
export interface ReallocateTasksResponse {
  studentId: number;
  remainingAmount: number;
  newTasksCount: number;
}

// ==================== 客服导入相关类型 ====================

/**
 * 客服导入响应
 */
export interface CustomerServiceImportResponse {
  totalImported: number;
  failedCount: number;
  failedDetails: string[];
}

// ==================== 学生补贴导入相关类型 ====================

/**
 * 学生补贴导入响应
 */
export interface StudentSubsidyImportResponse {
  importBatch: string;
  totalStudents: number;
  totalSubsidy: number;
  generatedTasks: number;
}

// ==================== 虚拟任务生成配置相关类型 ====================

/**
 * 虚拟任务生成配置
 */
export interface VirtualTaskGenerationConfig {
  enabled: boolean;
  daily_bonus_enabled: boolean;
  expired_task_regeneration_enabled: boolean;
  value_recycling_enabled: boolean;
  bonus_pool_task_enabled: boolean;
}

/**
 * 更新虚拟任务生成配置请求参数
 */
export interface UpdateVirtualTaskGenerationConfigParams {
  enabled?: boolean;
  daily_bonus_enabled?: boolean;
  expired_task_regeneration_enabled?: boolean;
  value_recycling_enabled?: boolean;
  bonus_pool_task_enabled?: boolean;
}
