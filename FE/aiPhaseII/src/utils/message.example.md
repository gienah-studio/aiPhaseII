# 统一消息提示工具使用说明

## 基本用法

```typescript
import { showSuccess, showError, showWarning, showInfo, showLoading } from '@/utils';

// 成功提示
showSuccess('操作成功！');

// 错误提示
showError('操作失败！');

// 警告提示
showWarning('请注意！');

// 信息提示
showInfo('提示信息');

// 加载提示
const hide = showLoading('正在处理...');
// 手动关闭
hide();
```

## 高级用法

```typescript
import { Message } from '@/utils';

// 带选项的提示
Message.success('操作成功！', {
  duration: 5, // 显示5秒
  onClose: () => console.log('消息关闭了')
});

// API错误处理
try {
  await someApiCall();
} catch (error) {
  Message.apiError(error, '默认错误信息');
}

// 网络错误处理
try {
  await someApiCall();
} catch (error) {
  Message.networkError(error);
}

// 表单验证错误
Message.validationError('请填写必填字段');

// 权限错误
Message.permissionError('您没有权限执行此操作');
```

## 类方法

```typescript
import { Message } from '@/utils';

// 销毁所有消息
Message.destroy();

// 销毁指定key的消息
Message.destroyByKey('my-message-key');
```

## 在组件中使用

```typescript
import React from 'react';
import { showSuccess, showApiError } from '@/utils';

const MyComponent = () => {
  const handleSubmit = async () => {
    try {
      await submitData();
      showSuccess('提交成功！');
    } catch (error) {
      showApiError(error, '提交失败');
    }
  };

  return (
    <button onClick={handleSubmit}>
      提交
    </button>
  );
};
```
