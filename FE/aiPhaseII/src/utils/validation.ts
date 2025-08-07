// 表单验证工具函数

// 手机号验证
export const validatePhone = (phone: string): boolean => {
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(phone);
};

// 密码强度验证
export const validatePassword = (password: string): {
  isValid: boolean;
  message: string;
} => {
  if (password.length < 6) {
    return { isValid: false, message: '密码至少6个字符' };
  }
  if (password.length > 50) {
    return { isValid: false, message: '密码最多50个字符' };
  }
  return { isValid: true, message: '密码格式正确' };
};

// 验证码验证
export const validateVerificationCode = (code: string): boolean => {
  const codeRegex = /^\d{6}$/;
  return codeRegex.test(code);
};

// 邮箱验证
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};
