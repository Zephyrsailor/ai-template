import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { FaUser, FaLock, FaEnvelope, FaUserPlus, FaSignInAlt } from 'react-icons/fa';
import { login, register, initAuthToken, getCurrentUser } from '../api/auth';

// 样式组件
const AuthContainer = styled.div`
  max-width: 400px;
  margin: 40px auto;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background-color: white;
`;

const Title = styled.h2`
  font-size: 1.5rem;
  color: #2d3748;
  margin-bottom: 20px;
  text-align: center;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

const FormGroup = styled.div`
  position: relative;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 15px 10px 40px;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  font-size: 1rem;
  transition: border-color 0.2s;
  
  &:focus {
    outline: none;
    border-color: #3182ce;
    box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
  }
`;

const IconWrapper = styled.div`
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #718096;
`;

const Button = styled.button`
  padding: 10px;
  border: none;
  border-radius: 5px;
  background-color: #3182ce;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    background-color: #2b6cb0;
  }
  
  &:disabled {
    background-color: #a0aec0;
    cursor: not-allowed;
  }
`;

const ToggleAction = styled.div`
  margin-top: 15px;
  text-align: center;
  font-size: 0.9rem;
  color: #718096;
  
  span {
    color: #3182ce;
    cursor: pointer;
    font-weight: 600;
    
    &:hover {
      text-decoration: underline;
    }
  }
`;

const ErrorMessage = styled.div`
  color: #e53e3e;
  margin-top: 15px;
  font-size: 0.9rem;
  text-align: center;
`;

const Auth = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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
  };
  
  return (
    <AuthContainer>
      <Title>{isLogin ? '登录' : '注册'}</Title>
      
      <Form onSubmit={handleSubmit}>
        <FormGroup>
          <IconWrapper>
            <FaUser />
          </IconWrapper>
          <Input 
            type="text" 
            name="username" 
            placeholder="用户名" 
            value={formData.username}
            onChange={handleChange}
            required
          />
        </FormGroup>
        
        {!isLogin && (
          <FormGroup>
            <IconWrapper>
              <FaEnvelope />
            </IconWrapper>
            <Input 
              type="email" 
              name="email" 
              placeholder="电子邮箱" 
              value={formData.email}
              onChange={handleChange}
              required
            />
          </FormGroup>
        )}
        
        <FormGroup>
          <IconWrapper>
            <FaLock />
          </IconWrapper>
          <Input 
            type="password" 
            name="password" 
            placeholder="密码" 
            value={formData.password}
            onChange={handleChange}
            required
          />
        </FormGroup>
        
        {!isLogin && (
          <FormGroup>
            <IconWrapper>
              <FaLock />
            </IconWrapper>
            <Input 
              type="password" 
              name="confirmPassword" 
              placeholder="确认密码" 
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
          </FormGroup>
        )}
        
        <Button type="submit" disabled={loading}>
          {loading ? (
            '处理中...'
          ) : isLogin ? (
            <>
              <FaSignInAlt /> 登录
            </>
          ) : (
            <>
              <FaUserPlus /> 注册
            </>
          )}
        </Button>
      </Form>
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      
      <ToggleAction>
        {isLogin ? '还没有账号？' : '已有账号？'} 
        <span onClick={toggleAuthMode}>
          {isLogin ? '注册' : '登录'}
        </span>
      </ToggleAction>
    </AuthContainer>
  );
};

export default Auth; 