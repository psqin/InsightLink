package com.psqin.controller;

import com.psqin.constant.JwtClaimsConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.*;
import com.psqin.domain.vo.SystemNoticeVO;
import com.psqin.domain.vo.UserVO;
import com.psqin.domain.entity.User;
import com.psqin.domain.vo.UserLoginVO;
import com.psqin.properties.JwtProperties;
import com.psqin.result.Result;
import com.psqin.mapper.NoticeMapper;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.service.UserService;
import com.psqin.utils.JwtUtil;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 *
 */
@Api(tags = "用户相关接口")
@RestController
@RequestMapping("/user")
@Slf4j
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtProperties jwtProperties;

    @Autowired
    private NoticeMapper noticeMapper;

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;


    @PostMapping("/login")
    public Result<UserLoginVO> login(@RequestBody UserLoginDTO userLoginDTO) {
        log.info("员工登录：{}" , userLoginDTO);
        User user = userService.login(userLoginDTO);

        HashMap<String, Object> claims = new HashMap<>();
        claims.put(JwtClaimsConstant.USER_ID, user.getId());
        claims.put(JwtClaimsConstant.ROLE_ID, user.getRoleId());
        String token = JwtUtil.createJWT(
                jwtProperties.getAdminSecretKey(),  //jwtProperties配置类，读取yml文件中的配置
                jwtProperties.getAdminTtl(),
                claims);

        UserLoginVO userLoginVO = UserLoginVO.builder()
                .id(user.getId())
                .userName(user.getUsername())
                .token(token)
                .avatar(user.getAvatar())
                .roleId(user.getRoleId())
                .realName(user.getRealName())
                .build();
        return Result.success(userLoginVO);
    }

    /**
     * 退出
     *
     * @return
     */
    @PostMapping("/logout")
    @ApiOperation("用户退出")
    public Result<String> logout() {
        return Result.success();
    }

    /**
     * 增加用户
     * @param userRegisterDTO
     * @return
     */
    @ApiOperation("用户注册")
    @PostMapping("/register")
    public Result save(@RequestBody UserRegisterDTO userRegisterDTO) {
        userService.save(userRegisterDTO);
        return Result.success();
    }

    /**
     * 修改用户信息
     * @param userDTO
     * @return
     */
    @ApiOperation("修改用户信息")
    @PostMapping("/update")
    public Result update(@RequestBody UserDTO userDTO) {
        userService.update(userDTO);
        return Result.success();
    }

    /**
     * 查询当前用户信息
     * @return
     */
    @ApiOperation("查询当前用户信息")
    @PostMapping("/info")
    public Result<UserVO> info() {
        Long userId = BaseContext.getCurrentId();
        User user = userService.getById(userId);
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return Result.success(userVO);
    }

    /**
     * 修改密码
     * @param passwordEditDTO
     * @return
     */
    @ApiOperation("修改密码")
    @PostMapping("/editPassword")
    public Result editPassword(@RequestBody PasswordEditDTO passwordEditDTO) {
        userService.editPassword(passwordEditDTO);
        return Result.success();
    }

    /**
     * 注销用户
     * @return
     */
    @ApiOperation("注销用户")
    @PostMapping("/deleteAccount")
    public Result deleteAccount() {
        userService.deleteAccount();
        return Result.success();
    }

    /**
     * 忘记密码
     * @param pwdForgetDTO
     * @return
     */
    @ApiOperation("忘记密码")
    @PostMapping("/forgetPassword")
    public Result editPassword(@RequestBody PwdForgetDTO pwdForgetDTO) {
        userService.forgetPassword(pwdForgetDTO);
        return Result.success();
    }

    @GetMapping("/notice/latest")
    @ApiOperation("查看通知（系统通知5条 + 导师通知5条）")
    public Result<Map<String, List<SystemNoticeVO>>> latestNotices() {
        Integer roleId = BaseContext.getRoleId();
        Long userId = BaseContext.getCurrentId();

        List<SystemNoticeVO> systemNotices = noticeMapper.listLatestByTypeAndPublisher(1, null, 5);

        Long teacherPublisherId = null;
        if (roleId != null && roleId == 2) {
            teacherPublisherId = userId;
        } else if (roleId != null && roleId == 3) {
            teacherPublisherId = tsGuidanceMapper.getTeacherUserIdByStudentUserId(userId);
        }

        List<SystemNoticeVO> teacherNotices = teacherPublisherId == null
                ? Collections.emptyList()
                : noticeMapper.listLatestByTypeAndPublisher(2, teacherPublisherId, 5);

        Map<String, List<SystemNoticeVO>> data = new LinkedHashMap<>();
        data.put("systemNotices", systemNotices);
        data.put("teacherNotices", teacherNotices);
        return Result.success(data);
    }
}
