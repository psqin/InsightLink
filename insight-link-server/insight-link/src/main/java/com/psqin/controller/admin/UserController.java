package com.psqin.controller.admin;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.AdminUserUpdateDTO;
import com.psqin.domain.entity.User;
import com.psqin.domain.vo.UserVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.UserMapper;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.DigestUtils;
import org.springframework.web.bind.annotation.*;

@Api(tags = "管理员-用户管理接口")
@RestController("AdminUserController")
@RequestMapping("/admin/user")
@Slf4j
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private UserMapper userMapper;

    @PutMapping("/{id}")
    @ApiOperation("修改用户")
    public Result update(@PathVariable Long id, @RequestBody AdminUserUpdateDTO dto) {
        Long currentId = BaseContext.getCurrentId();
        User currentUser = userMapper.getById(currentId);
        if (id == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        User existing = userMapper.getById(id);
        if (existing == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        boolean currentIsSuperAdmin = currentUser != null && "admin".equals(currentUser.getUsername()) && Integer.valueOf(1).equals(currentUser.getRoleId());
        boolean targetIsSuperAdmin = "admin".equals(existing.getUsername()) && Integer.valueOf(1).equals(existing.getRoleId());
        if (targetIsSuperAdmin && !currentIsSuperAdmin) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        User updateUser = new User();
        updateUser.setId(id);
        updateUser.setBirthday(dto.getBirthday());
        updateUser.setEmail(dto.getEmail());
        updateUser.setGender(dto.getGender());
        updateUser.setPhone(dto.getPhone());
        updateUser.setRealName(dto.getRealName());
        if (dto.getPassword() != null && !dto.getPassword().isEmpty()) {
            updateUser.setPassword(DigestUtils.md5DigestAsHex(dto.getPassword().getBytes()));
        }
        userMapper.update(updateUser);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除用户")
    public Result delete(@PathVariable Long id) {
        if (id == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        Long currentId = BaseContext.getCurrentId();
        if (id.equals(currentId)) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        User user = userMapper.getById(id);
        if (user == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        User currentUser = userMapper.getById(currentId);
        boolean currentIsSuperAdmin = currentUser != null && "admin".equals(currentUser.getUsername()) && Integer.valueOf(1).equals(currentUser.getRoleId());
        boolean targetIsSuperAdmin = "admin".equals(user.getUsername()) && Integer.valueOf(1).equals(user.getRoleId());
        if (targetIsSuperAdmin && !currentIsSuperAdmin) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        if (Integer.valueOf(1).equals(user.getRoleId()) && !currentIsSuperAdmin) {
            throw new AccountNotAllowException(MessageConstant.ADMIN_DELETE_NOT_ALLOW);
        }
        userMapper.deleteById(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("查询用户详情")
    public Result<UserVO> getById(@PathVariable Long id) {
        User user = userService.getById(id);
        if (user == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return Result.success(userVO);
    }

    @GetMapping("/page")
    @ApiOperation("分页查询用户（支持角色过滤、关键字模糊）")
    public Result<PageResult> page(@RequestParam(defaultValue = "1") Integer page,
                                   @RequestParam(defaultValue = "10") Integer pageSize,
                                   @RequestParam(required = false) Integer roleId,
                                   @RequestParam(required = false) String keyword,
                                   @RequestParam(required = false) String phone) {
        PageHelper.startPage(page, pageSize);
        Page<UserVO> p = userMapper.pageQuery(roleId, keyword, phone);
        return Result.success(new PageResult(p.getTotal(), p.getResult()));
    }
}
