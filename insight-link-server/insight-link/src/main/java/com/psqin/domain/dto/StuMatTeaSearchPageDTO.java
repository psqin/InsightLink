package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 *
 */
@Data
@ApiModel(description = "导师查询学生材料的条件")
public class StuMatTeaSearchPageDTO {

    private int page;

    private int pageSize ;

    private Integer materialType;

    @ApiModelProperty("学校ID")
    private Long universityId;

    @ApiModelProperty("学院ID")
    private Long collegeId;

    @ApiModelProperty("是否已评价：0-未评价，1-已评价")
    private Integer evaluated;

    @ApiModelProperty("学号")
    private String studentNo;

    @ApiModelProperty("真实姓名")
    private String realName;

    @ApiModelProperty("专业")
    private Long majorId;

    @ApiModelProperty("班级")
    private Long classId;

}
