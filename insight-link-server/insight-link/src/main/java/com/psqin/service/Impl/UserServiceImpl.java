package com.psqin.service.Impl;

import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.*;
import com.psqin.domain.entity.User;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.exception.AccountPasswordNotRightException;
import com.psqin.exception.BaseException;
import com.psqin.mapper.UserMapper;
import com.psqin.service.UserService;
import com.psqin.utils.NanoIdUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.DigestUtils;
import org.springframework.util.StringUtils;

/**
 *
 */
@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;


    @Override
    public User login(UserLoginDTO userLoginDTO) {
        String username = userLoginDTO.getUsername();
        String password = userLoginDTO.getPassword();
        String phone = userLoginDTO.getPhone();
        Integer roleId = userLoginDTO.getRoleId();

        User user = null;

        if(username == null || "".equals(username)){
            user = userMapper.getByPhone(phone, roleId);
        } else if (phone == null || "".equals(phone)){
            user = userMapper.getByUsername(username, roleId);
        }

        if(user == null){
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_NOT_FOUND);
        }

        password = DigestUtils.md5DigestAsHex(password.getBytes());

        if(!password.equals(user.getPassword())){
            throw new AccountPasswordNotRightException(MessageConstant.PASSWORD_ERROR);
        }

        return user;
    }

    @Override
    public void save(UserRegisterDTO userRegisterDTO) {
        // 校验手机号是否已存在
        User existUser = userMapper.getByPhone(userRegisterDTO.getPhone(), userRegisterDTO.getRoleId());
        if (existUser != null) {
            throw new AccountNotAllowException("手机号已注册，请登录");
        }

        User user = new User();
        BeanUtils.copyProperties(userRegisterDTO, user);
        user.setPassword(DigestUtils.md5DigestAsHex(userRegisterDTO.getPassword().getBytes()));

        // 生成唯一用户名
        String username;
        do {
            // 规则：NanoId 8位
            username = NanoIdUtils.randomNanoId(8);
        } while (userMapper.getByUsername(username, userRegisterDTO.getRoleId()) != null);
        user.setAvatar("https://psqin001.oss-cn-beijing.aliyuncs.com/Defaultavatar.png");
        user.setUsername(username);
        userMapper.insert(user);
    }

    @Override
    public void update(UserDTO userDTO) {
        User user = new User();
        BeanUtils.copyProperties(userDTO, user);
        // 强制设置ID为当前登录用户ID，防止越权修改
        user.setId(BaseContext.getCurrentId());
        userMapper.update(user);
    }

    @Override
    public User getById(Long id) {
        return userMapper.getById(id);
    }

    @Override
    public void editPassword(PasswordEditDTO passwordEditDTO) {

        // 校验旧密码
        String oldPwd = passwordEditDTO.getOldPassword();
        if (!StringUtils.hasText(oldPwd)) {
            throw new BaseException("旧密码不能为空");
        }
        // 校验新密码
        String newPwd = passwordEditDTO.getNewPassword();
        if (!StringUtils.hasText(newPwd)) {
            throw new BaseException("新密码不能为空");
        }

        // 1. 获取当前登录用户ID
        Long userId = BaseContext.getCurrentId();
        User user = userMapper.getById(userId);

        // 2. 校验旧密码是否正确
        String oldPassword = DigestUtils.md5DigestAsHex(passwordEditDTO.getOldPassword().getBytes());
        if (!user.getPassword().equals(oldPassword)) {
            throw new AccountPasswordNotRightException("原密码错误");
        }

        // 3. 更新新密码
        String newPassword = DigestUtils.md5DigestAsHex(passwordEditDTO.getNewPassword().getBytes());
        user.setPassword(newPassword);
        userMapper.update(user);
    }

    @Override
    public void deleteAccount() {
        Long userId = BaseContext.getCurrentId();
        // 数据库已设置级联删除，直接删除User表数据即可
        userMapper.deleteById(userId);
    }

    @Override
    public void forgetPassword(PwdForgetDTO pwdForgetDTO) {
        User existUser = null;
        String userMessage = pwdForgetDTO.getUserMessage();
        String password = pwdForgetDTO.getNewPassword();
        Integer roleId = pwdForgetDTO.getRoleId();
        String phoneRegex = "^\\d{11}$";

        if (userMessage != null && userMessage.matches(phoneRegex)) {
            // 是11位数字，按手机号查询
            existUser = userMapper.getByPhone(userMessage, roleId);
        } else if (userMessage != null && !"".equals(userMessage)) {
            // 不是11位数字且非空，按用户名查询
            existUser = userMapper.getByUsername(userMessage, roleId);
        }
        if(existUser == null){
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_NOT_FOUND);
        }
        password = DigestUtils.md5DigestAsHex(password.getBytes());

        User user = User.builder().id(existUser.getId()).password(password).build();

        userMapper.update(user);

    }
}
