import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// 解决walletRouter冲突问题
(function() {
  try {
    // 检查是否已定义walletRouter属性
    if (Object.prototype.hasOwnProperty.call(window, 'walletRouter') || 
        Object.getOwnPropertyDescriptor(window, 'walletRouter')) {
      console.log('walletRouter已存在，防止重复定义');
    } else {
      // 安全地定义walletRouter
      Object.defineProperty(window, 'walletRouter', {
        value: {},
        writable: true,
        configurable: true
      });
    }
  } catch (e) {
    console.warn('防止walletRouter错误', e);
  }
})();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
); 