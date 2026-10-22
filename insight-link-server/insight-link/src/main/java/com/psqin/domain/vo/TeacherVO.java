package com.psqin.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;
import java.io.Serializable;

@Data
@ApiModel(description = "导师详细信息VO")
public class TeacherVO implements Serializable {

    @ApiModelProperty(value = "主键ID")
    private Long id;

    @ApiModelProperty(value = "用户ID")
    private Long userId;

    @ApiModelProperty(value = "真实姓名")
    private String realName;

    @ApiModelProperty(value = "手机号")
    private String phone;

    @ApiModelProperty(value = "头像")
    private String avatar;

    @ApiModelProperty(value = "性别：0-保密, 1-男, 2-女")
    private Integer gender;

    @ApiModelProperty(value = "邮箱")
    private String email;

    @ApiModelProperty(value = "工号")
    private String teacherNo;

    @ApiModelProperty(value = "学校ID")
    private Long universityId;

    @ApiModelProperty(value = "学校名称")
    private String universityName;

    @ApiModelProperty(value = "院系ID")
    private Long deptId;

    @ApiModelProperty(value = "院系名称")
    private String deptName;

    @ApiModelProperty(value = "职称")
    private String title;

    @ApiModelProperty(value = "研究领域")
    private String researchField;
}
