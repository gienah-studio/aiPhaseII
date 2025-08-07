import React from 'react';
import { getToken, getUserInfo, clearAuthInfo, showSuccess } from '../utils';

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean>(false);
  const [user, setUser] = React.useState<any>(null);
  const [loading, setLoading] = React.useState<boolean>(true);

  React.useEffect(() => {
    const token = getToken();
    const userInfo = getUserInfo();
    
    if (token && userInfo) {
      setIsAuthenticated(true);
      setUser(userInfo);
    }
    
    setLoading(false);
  }, []);

  const logout = () => {
    clearAuthInfo();
    setIsAuthenticated(false);
    setUser(null);
    showSuccess('已退出登录');
    window.location.href = '/login';
  };

  return {
    isAuthenticated,
    user,
    loading,
    logout,
  };
};
