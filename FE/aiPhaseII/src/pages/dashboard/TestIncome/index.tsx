import React, { useState } from 'react';
import { Button, Card, message } from 'antd';
import { getAllStudentsDailyIncomeStats } from '../../../api';

const TestIncome: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const testAPI = async () => {
    try {
      setLoading(true);
      console.log('开始测试API...');
      
      const response = await getAllStudentsDailyIncomeStats();
      console.log('API响应成功:', response);
      
      setResult(response);
      message.success('API调用成功');
    } catch (error: any) {
      console.error('API调用失败:', error);
      message.error('API调用失败: ' + (error?.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="API测试页面" style={{ margin: 20 }}>
      <Button 
        type="primary" 
        onClick={testAPI} 
        loading={loading}
        style={{ marginBottom: 16 }}
      >
        测试学员收入统计API
      </Button>
      
      {result && (
        <div>
          <h3>API响应结果:</h3>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: 16, 
            borderRadius: 4,
            overflow: 'auto',
            maxHeight: 400
          }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </Card>
  );
};

export default TestIncome;
