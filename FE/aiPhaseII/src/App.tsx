import React from 'react';
import { ConfigProvider } from 'antd';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages';
import { Home, CustomerService, StudentModule, StudentIncome, TestIncome } from './pages/dashboard';
import { MessageProvider, MainLayout } from './components';
import { useAuth } from './hooks';
import { ROUTES } from './constants';

// 受保护的路由组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <>{children}</>;
};

// 主应用布局组件 - 包装所有受保护的路由
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <MainLayout>
      {children}
    </MainLayout>
  );
};

function App() {
  return (
    <ConfigProvider>
      <MessageProvider>
        <Router>
          <Routes>
            {/* 登录页面 */}
            <Route path={ROUTES.LOGIN} element={<Login />} />

            {/* 受保护的路由 - 使用统一布局 */}
            <Route
              path={ROUTES.HOME}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Home />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.CUSTOMER_SERVICE}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <CustomerService />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.STUDENT_MODULE}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <StudentModule />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.STUDENT_INCOME}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <StudentIncome />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.TEST_INCOME}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <TestIncome />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            {/* 默认重定向到首页 */}
            <Route path="/" element={<Navigate to={ROUTES.HOME} replace />} />

            {/* 404页面 */}
            <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
          </Routes>
        </Router>
      </MessageProvider>
    </ConfigProvider>
  );
}

export default App;
