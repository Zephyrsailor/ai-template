import { createGlobalStyle } from 'styled-components';

const GlobalStyles = createGlobalStyle`
  :root {
    --bg-primary: #f9fafc;
    --bg-secondary: #ffffff;
    --text-primary: #333333;
    --text-secondary: #666666;
    --accent-primary: #4a6cf7;
    --accent-secondary: #e2e8ff;
    --border-color: #e6e8ec;
    --shadow-color: rgba(0, 0, 0, 0.05);
    --error-color: #e53935;
    --success-color: #43a047;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  html, body {
    height: 100%;
    width: 100%;
    overflow: hidden;
    position: fixed;
    overscroll-behavior: none;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    color: var(--text-primary);
    background-color: var(--bg-primary);
    line-height: 1.5;
    font-size: 14px;
    -webkit-tap-highlight-color: transparent;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* 滚动条样式 */
  ::-webkit-scrollbar {
    width: 10px;
    height: 10px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 10px;
    border: 2px solid #f9fafc;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #a0a0a0;
  }
  
  /* 确保所有滚动容器都有触摸惯性滚动 */
  div {
    -webkit-overflow-scrolling: touch;
  }
  
  /* 改善按钮触摸体验 */
  button {
    touch-action: manipulation;
  }
`;

export default GlobalStyles; 