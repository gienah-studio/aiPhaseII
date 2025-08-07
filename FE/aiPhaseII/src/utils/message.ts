import { message as antdMessage } from 'antd';

// 消息提示配置
const messageConfig = {
  duration: 3, // 默认显示时间（秒）
  maxCount: 3, // 最大显示数量
};

// 配置全局消息提示
antdMessage.config(messageConfig);

// 消息类型枚举
export enum MessageType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
  LOADING = 'loading',
}

// 消息提示选项
export interface MessageOptions {
  duration?: number;
  onClose?: () => void;
  key?: string | number;
}

// 统一的消息提示工具类
export class Message {
  /**
   * 成功提示
   */
  static success(content: string, options?: MessageOptions) {
    return antdMessage.success(content, options?.duration, options?.onClose);
  }

  /**
   * 错误提示
   */
  static error(content: string, options?: MessageOptions) {
    return antdMessage.error(content, options?.duration, options?.onClose);
  }

  /**
   * 警告提示
   */
  static warning(content: string, options?: MessageOptions) {
    return antdMessage.warning(content, options?.duration, options?.onClose);
  }

  /**
   * 信息提示
   */
  static info(content: string, options?: MessageOptions) {
    return antdMessage.info(content, options?.duration, options?.onClose);
  }

  /**
   * 加载提示
   */
  static loading(content: string, options?: MessageOptions) {
    return antdMessage.loading(content, options?.duration, options?.onClose);
  }

  /**
   * 销毁所有消息
   */
  static destroy() {
    antdMessage.destroy();
  }

  /**
   * 销毁指定key的消息
   */
  static destroyByKey(key: string | number) {
    antdMessage.destroy(key);
  }

  /**
   * API错误处理
   */
  static apiError(error: any, defaultMessage = '操作失败，请稍后重试') {
    // 优先从apiResponse中获取错误信息（由响应拦截器设置）
    const errorMessage = error?.apiResponse?.message ||
                        error?.response?.data?.message ||
                        error?.message ||
                        defaultMessage;

    console.log('API错误详情:', {
      apiResponse: error?.apiResponse,
      responseData: error?.response?.data,
      message: error?.message,
      finalMessage: errorMessage
    });

    return this.error(errorMessage);
  }

  /**
   * 网络错误处理
   */
  static networkError(error: any) {
    if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('Network Error')) {
      return this.error('网络连接失败，请检查网络设置');
    }
    if (error?.code === 'TIMEOUT') {
      return this.error('请求超时，请稍后重试');
    }
    return this.apiError(error);
  }

  /**
   * 表单验证错误处理
   */
  static validationError(message: string) {
    return this.warning(message);
  }

  /**
   * 权限错误处理
   */
  static permissionError(message = '您没有权限执行此操作') {
    return this.error(message);
  }
}

// 导出便捷方法
export const showSuccess = Message.success;
export const showError = Message.error;
export const showWarning = Message.warning;
export const showInfo = Message.info;
export const showLoading = Message.loading;
export const showApiError = Message.apiError;
export const showNetworkError = Message.networkError;
export const showValidationError = Message.validationError;
export const showPermissionError = Message.permissionError;

// 默认导出
export default Message;
