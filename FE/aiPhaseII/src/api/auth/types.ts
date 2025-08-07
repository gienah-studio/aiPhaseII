// 用户基础信息
export interface UserInfo {
  id: string;
  username: string;
  phone?: string;
  email?: string;
  avatar?: string;
  createdAt?: string;
  updatedAt?: string;
}

// 认证响应 - 匹配实际API返回格式
export interface AuthResponse {
  code: number;
  data: {
    accessToken: string;
  };
  message: string;
}

// 旧的认证响应格式（保留兼容性）
export interface LegacyAuthResponse {
  token: string;
  user: UserInfo;
}

// 登录请求参数
export interface LoginRequest {
  username: string;
  password: string;
}

// 单个学员收入统计
export interface StudentIncomeStats {
  studentId: number;              // 学员ID
  studentName: string;            // 学员姓名
  yesterdayIncome: string;        // 昨日原始佣金总额
  yesterdayCompletedOrders: number;  // 昨日完成订单数
  commissionRate: string;         // 代理返佣比例（学员能拿到的比例）
  actualIncome: string;           // 实际到手金额
  phoneNumber: string;            // 手机号
}

// 所有学员收入统计响应
export interface AllStudentsIncomeStatsResponse {
  students: StudentIncomeStats[];  // 学员列表
  total: number;                   // 学员总数
  page: number;                    // 当前页码
  size: number;                    // 每页大小
  totalPages: number;              // 总页数
  statDate: string;                // 统计日期（YYYY-MM-DD）
}


