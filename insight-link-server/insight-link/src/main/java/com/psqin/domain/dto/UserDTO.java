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
@ApiModel(description = "用户数据模型")
public class UserDTO {

    @ApiModelProperty("密码")
    private String password;

    @ApiModelProperty("真实姓名")
    private String realName;

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

    @ApiModelProperty("邮箱")
    private String email;
}
