package com.psqin.domain.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.time.LocalDate;

/**
 *
 */
@Data
@ApiModel(description = "用户注册时传递的数据模型")
public class UserRegisterDTO {

    @ApiModelProperty("密码")
    private String password;

    @ApiModelProperty("真实姓名")
    private String realName;

    @ApiModelProperty("手机号")
    private String phone;

    @ApiModelProperty("头像路径")
    private String avatar;

    @ApiModelProperty("出生年月")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate birthday;

    /**
     * 性别：0-保密, 1-男, 2-女
     */
    @ApiModelProperty("性别")
    private Integer gender;

    /**
     * 角色ID：1-管理员, 2-导师, 3-学生
     */
    @ApiModelProperty("角色")
    private Integer roleId;

    @ApiModelProperty("邮箱")
    private String email;

}
