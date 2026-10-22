package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 *
 */
@Data
@ApiModel(description = "忘记密码参数")
public class PwdForgetDTO {

    @ApiModelProperty("用户名或手机号")
    private String userMessage;

    /**
     * 角色ID：1-管理员, 2-导师, 3-学生
     */
    @ApiModelProperty("角色")
    private Integer roleId;

    @ApiModelProperty(value = "新密码", required = true)
    private String newPassword;
}
