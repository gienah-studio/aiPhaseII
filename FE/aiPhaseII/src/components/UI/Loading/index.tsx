import React from 'react';
import { Spin } from 'antd';

interface LoadingProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  spinning?: boolean;
  children?: React.ReactNode;
}

const Loading: React.FC<LoadingProps> = ({
  size = 'default',
  tip = '加载中...',
  spinning = true,
  children,
}) => {
  if (children) {
    return (
      <Spin size={size} tip={tip} spinning={spinning}>
        {children}
      </Spin>
    );
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '200px'
    }}>
      <Spin size={size}>
        <div style={{ padding: '20px' }}>
          {tip}
        </div>
      </Spin>
    </div>
  );
};

export default Loading;
