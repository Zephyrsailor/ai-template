"""
输入验证器 - 统一处理输入验证逻辑
"""
import re
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from .constants import ValidationConstants, FileConstants
from .errors import ValidationException, FileTooLargeException, UnsupportedFileTypeException

class BaseValidator(ABC):
    """验证器基类"""
    
    @abstractmethod
    def validate(self, value: Any) -> bool:
        """验证输入值"""
        pass
    
    def require_valid(self, value: Any, field_name: str = "字段") -> None:
        """要求输入有效，如果无效则抛出异常"""
        if not self.validate(value):
            raise ValidationException(f"{field_name}验证失败", field_name)

class TextValidator(BaseValidator):
    """文本验证器"""
    
    def __init__(self, min_length: int = 0, max_length: int = None, pattern: str = None):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
    
    def validate(self, text: str) -> bool:
        """验证文本"""
        if not isinstance(text, str):
            return False
        
        # 长度检查
        if len(text) < self.min_length:
            return False
        
        if self.max_length and len(text) > self.max_length:
            return False
        
        # 模式检查
        if self.pattern and not self.pattern.match(text):
            return False
        
        return True
    
    def require_valid(self, text: str, field_name: str = "文本") -> None:
        """要求文本有效"""
        if not isinstance(text, str):
            raise ValidationException(f"{field_name}必须是字符串", field_name)
        
        if len(text) < self.min_length:
            raise ValidationException(f"{field_name}长度不能少于{self.min_length}字符", field_name)
        
        if self.max_length and len(text) > self.max_length:
            raise ValidationException(f"{field_name}长度不能超过{self.max_length}字符", field_name)
        
        if self.pattern and not self.pattern.match(text):
            raise ValidationException(f"{field_name}格式不正确", field_name)

class FileValidator(BaseValidator):
    """文件验证器"""
    
    def __init__(self, max_size: int = None, allowed_types: List[str] = None):
        self.max_size = max_size or FileConstants.MAX_FILE_SIZE
        self.allowed_types = allowed_types or FileConstants.ALLOWED_FILE_TYPES
    
    def validate(self, file_content: bytes, file_type: str = None, file_name: str = None) -> bool:
        """验证文件"""
        try:
            self.validate_file_size(file_content)
            if file_type:
                self.validate_file_type(file_type)
            if file_name:
                self.validate_file_name(file_name)
            return True
        except ValidationException:
            return False
    
    def validate_file_size(self, file_content: bytes) -> None:
        """验证文件大小"""
        if len(file_content) > self.max_size:
            raise FileTooLargeException(len(file_content), self.max_size)
    
    def validate_file_type(self, file_type: str) -> None:
        """验证文件类型"""
        if file_type not in self.allowed_types:
            raise UnsupportedFileTypeException(file_type, self.allowed_types)
    
    def validate_file_name(self, file_name: str) -> None:
        """验证文件名"""
        if not file_name or len(file_name.strip()) == 0:
            raise ValidationException("文件名不能为空", "file_name")
        
        if len(file_name) > ValidationConstants.MAX_FILENAME_LENGTH:
            raise ValidationException(f"文件名长度不能超过{ValidationConstants.MAX_FILENAME_LENGTH}字符", "file_name")
        
        # 检查文件名中的非法字符
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in illegal_chars:
            if char in file_name:
                raise ValidationException(f"文件名不能包含字符: {char}", "file_name")

class EmailValidator(BaseValidator):
    """邮箱验证器"""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __init__(self):
        self.pattern = re.compile(self.EMAIL_PATTERN)
    
    def validate(self, email: str) -> bool:
        """验证邮箱"""
        if not isinstance(email, str):
            return False
        return bool(self.pattern.match(email))
    
    def require_valid(self, email: str, field_name: str = "邮箱") -> None:
        """要求邮箱有效"""
        if not self.validate(email):
            raise ValidationException(f"{field_name}格式不正确", field_name)

class PasswordValidator(BaseValidator):
    """密码验证器"""
    
    def __init__(self, min_length: int = None, require_uppercase: bool = False, 
                 require_lowercase: bool = False, require_digit: bool = False, 
                 require_special: bool = False):
        self.min_length = min_length or ValidationConstants.MIN_PASSWORD_LENGTH
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
    
    def validate(self, password: str) -> bool:
        """验证密码"""
        if not isinstance(password, str):
            return False
        
        if len(password) < self.min_length:
            return False
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            return False
        
        if self.require_lowercase and not any(c.islower() for c in password):
            return False
        
        if self.require_digit and not any(c.isdigit() for c in password):
            return False
        
        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
        
        return True
    
    def require_valid(self, password: str, field_name: str = "密码") -> None:
        """要求密码有效"""
        if not isinstance(password, str):
            raise ValidationException(f"{field_name}必须是字符串", field_name)
        
        if len(password) < self.min_length:
            raise ValidationException(f"{field_name}长度不能少于{self.min_length}字符", field_name)
        
        requirements = []
        if self.require_uppercase and not any(c.isupper() for c in password):
            requirements.append("大写字母")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            requirements.append("小写字母")
        
        if self.require_digit and not any(c.isdigit() for c in password):
            requirements.append("数字")
        
        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            requirements.append("特殊字符")
        
        if requirements:
            raise ValidationException(f"{field_name}必须包含: {', '.join(requirements)}", field_name)

class ValidationManager:
    """验证管理器 - 统一的验证入口"""
    
    def __init__(self):
        # 预定义的验证器
        self.knowledge_base_name_validator = TextValidator(
            min_length=ValidationConstants.MIN_KB_NAME_LENGTH,
            max_length=ValidationConstants.MAX_KB_NAME_LENGTH
        )
        self.knowledge_base_description_validator = TextValidator(
            max_length=ValidationConstants.MAX_KB_DESCRIPTION_LENGTH
        )
        self.file_validator = FileValidator()
        self.email_validator = EmailValidator()
        self.password_validator = PasswordValidator()
        self.username_validator = TextValidator(
            min_length=ValidationConstants.MIN_USERNAME_LENGTH,
            max_length=ValidationConstants.MAX_USERNAME_LENGTH,
            pattern=r'^[a-zA-Z0-9_]+$'  # 只允许字母、数字和下划线
        )
    
    def validate_knowledge_base_name(self, name: str) -> None:
        """验证知识库名称"""
        self.knowledge_base_name_validator.require_valid(name, "知识库名称")
    
    def validate_knowledge_base_description(self, description: str) -> None:
        """验证知识库描述"""
        if description:  # 描述是可选的
            self.knowledge_base_description_validator.require_valid(description, "知识库描述")
    
    def validate_file_upload(self, file_content: bytes, file_type: str = None, file_name: str = None) -> None:
        """验证文件上传"""
        self.file_validator.validate_file_size(file_content)
        if file_type:
            self.file_validator.validate_file_type(file_type)
        if file_name:
            self.file_validator.validate_file_name(file_name)
    
    def validate_email(self, email: str) -> None:
        """验证邮箱"""
        self.email_validator.require_valid(email)
    
    def validate_password(self, password: str) -> None:
        """验证密码"""
        self.password_validator.require_valid(password)
    
    def validate_username(self, username: str) -> None:
        """验证用户名"""
        self.username_validator.require_valid(username, "用户名")

# 全局验证管理器实例
validation_manager = ValidationManager() 