import React, { useState } from 'react';
import styled from 'styled-components';
import { FaUser, FaSignOutAlt, FaKey, FaCheck, FaTimes } from 'react-icons/fa';
import { changePassword, logout } from '../api/auth';

// 样式组件
const ProfileContainer = styled.div`
  max-width: 500px;
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

const ProfileSection = styled.div`
  margin-bottom: 25px;
`;

const SectionTitle = styled.h3`
  font-size: 1.1rem;
  margin-bottom: 15px;
  color: #4a5568;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
`;

const UserInfo = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 15px;
`;

const UserIcon = styled.div`
  background-color: #e2e8f0;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  
  svg {
    font-size: 24px;
    color: #4a5568;
  }
`;

const UserDetails = styled.div`
  flex-grow: 1;
`;

const UserName = styled.div`
  font-weight: 600;
  font-size: 1.1rem;
`;

const UserEmail = styled.div`
  color: #718096;
  font-size: 0.9rem;
`;

const UserRole = styled.div`
  color: #2b6cb0;
  font-size: 0.8rem;
  margin-top: 3px;
  font-weight: 600;
  text-transform: uppercase;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  font-size: 0.9rem;
  margin-bottom: 5px;
  color: #4a5568;
`;

const Input = styled.input`
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  font-size: 1rem;
  
  &:focus {
    outline: none;
    border-color: #3182ce;
    box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
  }
`;

const Button = styled.button`
  padding: 10px;
  border: none;
  border-radius: 5px;
  background-color: ${props => props.secondary ? '#718096' : '#3182ce'};
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: ${props => props.mt || '0'};
  
  &:hover {
    background-color: ${props => props.secondary ? '#4a5568' : '#2b6cb0'};
  }
  
  &:disabled {
    background-color: #a0aec0;
    cursor: not-allowed;
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 10px;
  margin-top: 10px;
`;

const Message = styled.div`
  padding: 10px;
  margin: 10px 0;
  border-radius: 5px;
  text-align: center;
  background-color: ${props => props.success ? '#c6f6d5' : '#fed7d7'};
  color: ${props => props.success ? '#2f855a' : '#c53030'};
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
`;

const UserProfile = ({ user, onLogout }) => {
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', success: false });
  
  // 处理输入变化
  const handleChange = (e) => {
    setPasswordData({
      ...passwordData,
      [e.target.name]: e.target.value
    });
  };
  
  // 验证表单
  const validateForm = () => {
    if (!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword) {
      setMessage({ text: '请填写所有字段', success: false });
      return false;
    }
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setMessage({ text: '新密码两次输入不一致', success: false });
      return false;
    }
    
    if (passwordData.newPassword.length < 6) {
      setMessage({ text: '新密码长度至少为6个字符', success: false });
      return false;
    }
    
    return true;
  };
  
  // 修改密码
  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    
    try {
      const result = await changePassword(
        passwordData.currentPassword,
        passwordData.newPassword
      );
      
      if (result.success) {
        setMessage({ text: '密码修改成功', success: true });
        // 清空表单
        setPasswordData({
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        });
        // 关闭修改密码表单
        setTimeout(() => {
          setShowPasswordForm(false);
          setMessage({ text: '', success: false });
        }, 2000);
      } else {
        setMessage({ text: result.message || '密码修改失败', success: false });
      }
    } catch (error) {
      setMessage({ text: error.message || '发生错误', success: false });
    } finally {
      setLoading(false);
    }
  };
  
  // 取消修改密码
  const handleCancel = () => {
    setShowPasswordForm(false);
    setPasswordData({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
    setMessage({ text: '', success: false });
  };
  
  // 退出登录
  const handleLogout = () => {
    logout();
    onLogout();
  };
  
  // 获取角色中文名
  const getRoleName = (role) => {
    switch (role) {
      case 'admin':
        return '管理员';
      case 'user':
        return '普通用户';
      default:
        return role;
    }
  };
  
  return (
    <ProfileContainer>
      <Title>个人资料</Title>
      
      <ProfileSection>
        <SectionTitle>基本信息</SectionTitle>
        <UserInfo>
          <UserIcon>
            <FaUser />
          </UserIcon>
          <UserDetails>
            <UserName>{user.username}</UserName>
            <UserEmail>{user.email}</UserEmail>
            <UserRole>{getRoleName(user.role)}</UserRole>
          </UserDetails>
        </UserInfo>
      </ProfileSection>
      
      <ProfileSection>
        <SectionTitle>账户安全</SectionTitle>
        
        {showPasswordForm ? (
          <>
            <Form onSubmit={handleChangePassword}>
              <FormGroup>
                <Label>当前密码</Label>
                <Input 
                  type="password" 
                  name="currentPassword" 
                  value={passwordData.currentPassword}
                  onChange={handleChange}
                  required
                />
              </FormGroup>
              
              <FormGroup>
                <Label>新密码</Label>
                <Input 
                  type="password" 
                  name="newPassword" 
                  value={passwordData.newPassword}
                  onChange={handleChange}
                  required
                />
              </FormGroup>
              
              <FormGroup>
                <Label>确认新密码</Label>
                <Input 
                  type="password" 
                  name="confirmPassword" 
                  value={passwordData.confirmPassword}
                  onChange={handleChange}
                  required
                />
              </FormGroup>
              
              {message.text && (
                <Message success={message.success}>
                  {message.success ? <FaCheck /> : <FaTimes />}
                  {message.text}
                </Message>
              )}
              
              <ButtonGroup>
                <Button type="submit" disabled={loading}>
                  {loading ? '处理中...' : '确认修改'}
                </Button>
                <Button type="button" secondary onClick={handleCancel} disabled={loading}>
                  取消
                </Button>
              </ButtonGroup>
            </Form>
          </>
        ) : (
          <Button onClick={() => setShowPasswordForm(true)}>
            <FaKey /> 修改密码
          </Button>
        )}
      </ProfileSection>
      
      <Button secondary mt="20px" onClick={handleLogout}>
        <FaSignOutAlt /> 退出登录
      </Button>
    </ProfileContainer>
  );
};

export default UserProfile; 