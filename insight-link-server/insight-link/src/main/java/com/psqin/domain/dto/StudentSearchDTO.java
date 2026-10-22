package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 *
 */
@Data
@ApiModel(description = "导师查询学生条件")
public class StudentSearchDTO {

    @ApiModelProperty("页码")
    private int page;

    @ApiModelProperty("每页记录数")
    private int pageSize;

    @ApiModelProperty("学号")
    private String studentNo;

    @ApiModelProperty("专业")
    private Long majorId;

    @ApiModelProperty("班级")
    private Long classId;

    @ApiModelProperty("入学年份")
    private Integer entryYear;
}
