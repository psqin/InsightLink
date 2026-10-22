package com.psqin.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;
import java.io.Serializable;

@Data
@ApiModel(description = "学生详细信息VO")
public class StudentVO implements Serializable {

    @ApiModelProperty(value = "主键ID")
    private Long id;

    @ApiModelProperty(value = "用户ID")
    private Long userId;

    @ApiModelProperty(value = "学号")
    private String studentNo;

    @ApiModelProperty(value = "学校ID")
    private Long universityId;

    @ApiModelProperty(value = "学校名称")
    private String universityName;

    @ApiModelProperty(value = "学院ID")
    private Long collegeId;

    @ApiModelProperty(value = "学院名称")
    private String collegeName;

    @ApiModelProperty(value = "专业ID")
    private Long majorId;

    @ApiModelProperty(value = "专业名称")
    private String majorName;

    @ApiModelProperty(value = "班级ID")
    private Long classId;

    @ApiModelProperty(value = "班级名称")
    private String className;

    @ApiModelProperty(value = "入学年份")
    private Integer entryYear;

    @ApiModelProperty(value = "绑定状态：0-未绑定导师，1-已绑定导师")
    private Integer bindStatus;

    @ApiModelProperty(value = "姓名")
    private String realName;

    @ApiModelProperty(value = "头像")
    private String avatar;

    @ApiModelProperty(value = "性别")
    private Integer gender;
}
