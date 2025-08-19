import React from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '../../../api/auth';
import type { LoginRequest } from '../../../api/auth/types';
import { setToken, setUserInfo } from '../../../utils';
import { ROUTES } from '../../../constants';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: LoginRequest) => {
    setLoading(true);
    try {
      const response = await login(values);

      // 检查响应格式并保存token
      if (response.code === 200 && response.data?.accessToken) {
        // 保存accessToken
        setToken(response.data.accessToken);

        // 创建用户信息对象（从登录表单数据中获取用户名）
        const userInfo = {
          id: '', // 后续可以从其他接口获取
          username: values.username,
        };
        setUserInfo(userInfo);

        message.success(response.message || '登录成功！');

        // 延迟跳转，让用户看到成功提示
        setTimeout(() => {
          window.location.href = ROUTES.HOME;
        }, 1000);
      } else {
        throw new Error(response.message || '登录响应格式错误');
      }
    } catch (error: any) {
      console.error('登录失败 - 完整错误对象:', error);
      console.error('错误响应数据:', error?.response?.data);
      console.error('错误消息:', error?.message);
      console.error('API响应:', error?.apiResponse);

      // 直接尝试获取错误消息，支持detail字段
      const errorMsg = error?.response?.data?.detail ||
                      error?.response?.data?.message ||
                      error?.apiResponse?.detail ||
                      error?.apiResponse?.message ||
                      error?.message ||
                      '登录失败，请检查用户名和密码';

      console.error('最终错误消息:', errorMsg);

      // 直接使用antd的message显示错误
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card
        style={{
          width: 400,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          borderRadius: '8px'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
            用户登录
          </Title>
          <Text type="secondary">
            欢迎回来，请输入您的账号信息
          </Text>
        </div>

        <Form
          form={form}
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名!' },
              { min: 3, message: '用户名至少3个字符!' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码!' },
              { min: 6, message: '密码至少6个字符!' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              style={{ width: '100%', height: '40px' }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
