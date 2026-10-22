package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@Data
@ApiModel(description = "管理员端-学生分页查询条件")
public class AdminStudentSearchDTO {

    @ApiModelProperty("页码")
    private Integer page = 1;

    @ApiModelProperty("每页记录数")
    private Integer pageSize = 10;

    @ApiModelProperty("姓名（模糊）")
    private String realName;

    @ApiModelProperty("学号（模糊）")
    private String studentNo;

    @ApiModelProperty("学校ID")
    private Long universityId;

    @ApiModelProperty("学院ID")
    private Long collegeId;

    @ApiModelProperty("专业ID")
    private Long majorId;

    @ApiModelProperty("班级ID")
    private Long classId;

    @ApiModelProperty("入学年份")
    private Integer entryYear;

    @ApiModelProperty("绑定状态：0-未绑定，1-已绑定")
    private Integer bindStatus;
}

