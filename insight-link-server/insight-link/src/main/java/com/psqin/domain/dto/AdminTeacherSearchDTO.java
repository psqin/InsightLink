package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@Data
@ApiModel(description = "管理员端-导师分页查询条件")
public class AdminTeacherSearchDTO {

    @ApiModelProperty("页码")
    private Integer page = 1;

    @ApiModelProperty("每页记录数")
    private Integer pageSize = 10;

    @ApiModelProperty("姓名（模糊）")
    private String realName;

    @ApiModelProperty("工号（模糊）")
    private String teacherNo;

    @ApiModelProperty("学校ID")
    private Long universityId;

    @ApiModelProperty("院系ID")
    private Long deptId;

    @ApiModelProperty("职称（模糊）")
    private String title;
}

