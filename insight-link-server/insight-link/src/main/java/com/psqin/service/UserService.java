package com.psqin.service;

import com.psqin.domain.dto.*;
import com.psqin.domain.entity.User;

/**
 *
 */
public interface UserService {

    /**
     * 用户登录
     * @param userLoginDTO
     * @return
     */
    User login(UserLoginDTO userLoginDTO);

    /**
     * 新增用户
     * @param userRegisterDTO
     */
    void save(UserRegisterDTO userRegisterDTO);


    /**
     * 修改用户信息
     * @param userDTO
     */
    void update(UserDTO userDTO);

    /**
     * 根据ID查询用户
     * @param id
     * @return
     */
    User getById(Long id);

    /**
     * 修改密码
     * @param passwordEditDTO
     */
    void editPassword(PasswordEditDTO passwordEditDTO);

    /**
     * 注销当前用户
     */
    void deleteAccount();

    void forgetPassword(PwdForgetDTO pwdForgetDTO);
}
