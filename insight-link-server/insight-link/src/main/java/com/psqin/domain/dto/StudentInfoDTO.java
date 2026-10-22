package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Positive;

/**
 *
 */
@Data
@ApiModel(description = "学生信息传递的数据模型")
public class StudentInfoDTO {

    @NotBlank(message = "学号不能为空")
    @ApiModelProperty(value = "学号", required = true, example = "20220305028")
    private String studentNo;

    @NotNull(message = "学校ID不能为空")
    @Positive(message = "学校ID必须为正整数")
    @ApiModelProperty(value = "学校ID", required = true, example = "1")
    private Long universityId;

    @NotNull(message = "院系ID不能为空")
    @Positive(message = "院系ID必须为正整数")
    @ApiModelProperty(value = "院系ID", required = true, example = "1")
    private Long collegeId;

    @NotNull(message = "专业ID不能为空")
    @Positive(message = "专业ID必须为正整数")
    @ApiModelProperty(value = "专业ID", required = true, example = "2")
    private Long majorId;

    @NotNull(message = "班级ID不能为空")
    @Positive(message = "班级ID必须为正整数")
    @ApiModelProperty(value = "班级ID", required = true, example = "3")
    private Long classId;

    @NotNull(message = "入学年份不能为空")
    @Positive(message = "入学年份必须为正整数")
    @ApiModelProperty(value = "入学年份", required = true, example = "2022")
    private Integer entryYear;
}
