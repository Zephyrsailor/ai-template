import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { FaUser, FaLock, FaEnvelope, FaUserPlus, FaSignInAlt, FaEye, FaEyeSlash } from 'react-icons/fa';
import { RiRobot2Line } from 'react-icons/ri';
import { login, register, initAuthToken, getCurrentUser } from '../api/auth';

// 样式组件
const AuthWrapper = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="75" cy="75" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="10" r="0.5" fill="rgba(255,255,255,0.05)"/><circle cx="10" cy="60" r="0.5" fill="rgba(255,255,255,0.05)"/><circle cx="90" cy="40" r="0.5" fill="rgba(255,255,255,0.05)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
    opacity: 0.3;
  }
`;

const AuthContainer = styled.div`
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04),
    0 0 0 1px rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  z-index: 1;
`;

const LogoSection = styled.div`
  text-align: center;
  margin-bottom: 32px;
`;

const LogoIcon = styled.div`
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
`;

const Title = styled.h1`
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px;
  letter-spacing: -0.025em;
`;

const Subtitle = styled.p`
  font-size: 16px;
  color: #6b7280;
  margin: 0;
  font-weight: 400;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

const FormGroup = styled.div`
  position: relative;
`;

const Label = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
`;

const InputWrapper = styled.div`
  position: relative;
`;

const Input = styled.input`
  width: 100%;
  padding: 16px 16px 16px 48px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  font-size: 16px;
  background: #ffffff;
  transition: all 0.2s ease;
  color: #111827;
  
  &::placeholder {
    color: #9ca3af;
  }
  
  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
    background: #ffffff;
  }
  
  &:hover:not(:focus) {
    border-color: #d1d5db;
  }
`;

const InputIcon = styled.div`
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-size: 16px;
  transition: color 0.2s ease;
  
  ${Input}:focus + & {
    color: #6366f1;
  }
`;

const PasswordToggle = styled.button`
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: color 0.2s ease;
  
  &:hover {
    color: #6b7280;
  }
  
  &:focus {
    outline: none;
    color: #6366f1;
  }
`;

const Button = styled.button`
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
  
  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    background: #d1d5db;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
`;

const LoadingSpinner = styled.div`
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const Divider = styled.div`
  margin: 24px 0;
  text-align: center;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 1px;
    background: #e5e7eb;
  }
  
  span {
    background: rgba(255, 255, 255, 0.95);
    padding: 0 16px;
    color: #6b7280;
    font-size: 14px;
    position: relative;
  }
`;

const ToggleAction = styled.div`
  text-align: center;
  font-size: 14px;
  color: #6b7280;
  
  button {
    background: none;
    border: none;
    color: #6366f1;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    padding: 0;
    margin-left: 4px;
    
    &:hover {
      text-decoration: underline;
    }
    
    &:focus {
      outline: none;
      text-decoration: underline;
    }
  }
`;

const ErrorMessage = styled.div`
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &::before {
    content: '⚠️';
    font-size: 16px;
  }
`;

const Auth = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    confirmPassword: ''
  });
  
  useEffect(() => {
    // 检查是否已登录
    const checkAuth = async () => {
      if (initAuthToken()) {
        const result = await getCurrentUser();
        if (result.success) {
          onAuthSuccess(result.data);
        }
      }
    };
    
    checkAuth();
  }, [onAuthSuccess]);
  
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // 清除错误信息
    if (error) setError('');
  };
  
  const validateForm = () => {
    // 重置错误
    setError('');
    
    // 表单验证
    if (!formData.username || !formData.password) {
      setError('请填写所有必填字段');
      return false;
    }
    
    if (!isLogin) {
      // 注册表单验证
      if (!formData.email) {
        setError('请填写电子邮箱');
        return false;
      }
      
      if (formData.password !== formData.confirmPassword) {
        setError('两次输入的密码不一致');
        return false;
      }
      
      if (formData.password.length < 6) {
        setError('密码长度至少为6个字符');
        return false;
      }
    }
    
    return true;
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    
    try {
      if (isLogin) {
        // 登录
        console.log('尝试登录:', formData.username);
        const result = await login(formData.username, formData.password);
        console.log('登录结果:', result);
        
        if (result.success) {
          // 获取用户信息
          const userResult = await getCurrentUser();
          console.log('获取用户信息结果:', userResult);
          
          if (userResult.success) {
            onAuthSuccess(userResult.data);
          } else {
            setError(userResult.message);
          }
        } else {
          setError(result.message);
        }
      } else {
        // 注册
        console.log('尝试注册:', formData.username, formData.email);
        const result = await register({
          username: formData.username,
          email: formData.email,
          password: formData.password
        });
        console.log('注册结果:', result);
        
        if (result.success) {
          // 注册成功后自动登录
          const loginResult = await login(formData.username, formData.password);
          if (loginResult.success) {
            const userResult = await getCurrentUser();
            if (userResult.success) {
              onAuthSuccess(userResult.data);
            } else {
              setError(userResult.message);
            }
          } else {
            setError(loginResult.message);
          }
        } else {
          setError(result.message);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleAuthMode = () => {
    setIsLogin(!isLogin);
    setError(''); // 切换模式时清除错误
    setFormData({
      username: '',
      password: '',
      email: '',
      confirmPassword: ''
    });
  };
  
  return (
    <AuthWrapper>
      <AuthContainer>
        <LogoSection>
          <LogoIcon>
            <RiRobot2Line size={32} color="white" />
          </LogoIcon>
          <Title>{isLogin ? '欢迎回来' : '创建账户'}</Title>
          <Subtitle>
            {isLogin ? '登录您的AI助手账户' : '开始您的AI助手之旅'}
          </Subtitle>
        </LogoSection>
        
        <Form onSubmit={handleSubmit}>
          <FormGroup>
            <Label>用户名</Label>
            <InputWrapper>
              <Input 
                type="text" 
                name="username" 
                placeholder="请输入用户名" 
                value={formData.username}
                onChange={handleChange}
                required
              />
              <InputIcon>
                <FaUser />
              </InputIcon>
            </InputWrapper>
          </FormGroup>
          
          {!isLogin && (
            <FormGroup>
              <Label>电子邮箱</Label>
              <InputWrapper>
                <Input 
                  type="email" 
                  name="email" 
                  placeholder="请输入电子邮箱" 
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
                <InputIcon>
                  <FaEnvelope />
                </InputIcon>
              </InputWrapper>
            </FormGroup>
          )}
          
          <FormGroup>
            <Label>密码</Label>
            <InputWrapper>
              <Input 
                type={showPassword ? "text" : "password"}
                name="password" 
                placeholder="请输入密码" 
                value={formData.password}
                onChange={handleChange}
                required
              />
              <InputIcon>
                <FaLock />
              </InputIcon>
              <PasswordToggle 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <FaEyeSlash /> : <FaEye />}
              </PasswordToggle>
            </InputWrapper>
          </FormGroup>
          
          {!isLogin && (
            <FormGroup>
              <Label>确认密码</Label>
              <InputWrapper>
                <Input 
                  type={showConfirmPassword ? "text" : "password"}
                  name="confirmPassword" 
                  placeholder="请再次输入密码" 
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                />
                <InputIcon>
                  <FaLock />
                </InputIcon>
                <PasswordToggle 
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
                </PasswordToggle>
              </InputWrapper>
            </FormGroup>
          )}
          
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <LoadingSpinner />
                处理中...
              </>
            ) : isLogin ? (
              <>
                <FaSignInAlt />
                登录
              </>
            ) : (
              <>
                <FaUserPlus />
                注册
              </>
            )}
          </Button>
        </Form>
        
        {error && <ErrorMessage>{error}</ErrorMessage>}
        
        <Divider>
          <span>或</span>
        </Divider>
        
        <ToggleAction>
          {isLogin ? '还没有账号？' : '已有账号？'}
          <button type="button" onClick={toggleAuthMode}>
            {isLogin ? '立即注册' : '立即登录'}
          </button>
        </ToggleAction>
      </AuthContainer>
    </AuthWrapper>
  );
};

export default Auth; 