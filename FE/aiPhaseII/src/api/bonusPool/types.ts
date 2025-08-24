/**
 * 奖金池汇总信息
 */
export interface BonusPoolSummary {
  poolDate: string;
  bonusPool: {
    totalAmount: number;
    remainingAmount: number;
    generatedAmount: number;
    completedAmount: number;
    exists: boolean;
  };
  qualifiedStudents: {
    count: number;
    achievementDate: string;
    students: Array<{
      studentId: number;
      studentName: string;
      completedAmount: number;
      dailyTarget: number;
    }>;
  };
  summary: {
    poolTotal: number;
    eligibleCount: number;
    averagePerPerson: number;
  };
}

/**
 * 每日补贴统计数据
 */
export interface DailySubsidyStats {
  dateRange: {
    startDate: string;
    endDate: string;
    days: number;
  };
  dailyStats: Array<{
    date: string;
    subsidyTotalAmount: number;
    remainingAmount: number;
    actualEarnedAmount: number;
    completionRate: number;
    tasksGenerated: number;
    tasksCompleted: number;
    activeStudentsCount: number;
    bonusPool: {
      totalAmount: number;
      remainingAmount: number;
      generatedAmount: number;
      completedAmount: number;
    };
    achievementStats: {
      totalStudents: number;
      achievedStudents: number;
      totalCompletedAmount: number;
    };
  }>;
  summary: {
    totalSubsidyAmount: number;
    totalEarnedAmount: number;
    totalTasksGenerated: number;
    totalTasksCompleted: number;
    overallCompletionRate: number;
  };
}

/**
 * 每日补贴统计查询参数
 */
export interface DailySubsidyStatsParams {
  startDate?: string;
  endDate?: string;
  days?: number;
}