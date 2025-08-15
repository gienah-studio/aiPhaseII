// 测试批量操作功能的脚本
import ResourceAPI from './api/resources';

// 测试批量删除功能
export const testBatchDelete = async () => {
  try {
    console.log('测试批量删除功能...');
    const response = await ResourceAPI.batchDeleteResources(['test-id-1', 'test-id-2']);
    console.log('批量删除响应:', response);
    return response.data;
  } catch (error) {
    console.error('批量删除测试失败:', error);
    throw error;
  }
};

// 测试批量移动分类功能
export const testBatchMoveCategory = async () => {
  try {
    console.log('测试批量移动分类功能...');
    const response = await ResourceAPI.batchMoveCategoryResources(
      ['test-id-1', 'test-id-2'], 
      'target-category-id'
    );
    console.log('批量移动分类响应:', response);
    return response.data;
  } catch (error) {
    console.error('批量移动分类测试失败:', error);
    throw error;
  }
};

// 导出测试函数
export default {
  testBatchDelete,
  testBatchMoveCategory
};