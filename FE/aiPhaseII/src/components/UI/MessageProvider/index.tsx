import React from 'react';
import { message } from 'antd';

interface MessageProviderProps {
  children: React.ReactNode;
}

const MessageProvider: React.FC<MessageProviderProps> = ({ children }) => {
  React.useEffect(() => {
    // 全局配置消息提示
    message.config({
      top: 100,
      duration: 3,
      maxCount: 3,
      rtl: false,
    });
  }, []);

  return <>{children}</>;
};

export default MessageProvider;
