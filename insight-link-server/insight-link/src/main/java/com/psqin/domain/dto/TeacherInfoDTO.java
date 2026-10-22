package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.*;

/**
 *
 */
@Data
@ApiModel(description = "导师信息传递的数据模型")
public class TeacherInfoDTO {

    @NotBlank(message = "教师编号不能为空")
    @Pattern(regexp = "^[0-9]{4,10}$", message = "教师编号必须为4-10位数字")
    @ApiModelProperty(value = "教师编号（工号）", required = true, example = "2022031", notes = "格式为4-10位数字，如20220317")
    private String teacherNo;

    @NotNull(message = "学校ID不能为空")
    @Positive(message = "学校ID必须为正整数")
    @ApiModelProperty(value = "学校ID（关联universities表主键）", required = true, example = "1", notes = "需与universities表中的id一致")
    private Long universityId;

    /**
     * 所属院系ID（关联sys_dept表，dept_type=1）
     */
    @NotNull(message = "院系ID不能为空")
    @Positive(message = "院系ID必须为正整数")
    @ApiModelProperty(value = "院系ID（关联sys_dept表主键，dept_type=1）", required = true, example = "1", notes = "需为sys_dept表中类型为院系（dept_type=1）的ID")
    private Long deptId;

    /**
     * 职称：教授/副教授/讲师/助教等
     */
    @NotBlank(message = "职称不能为空")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5]{2,10}$", message = "职称必须为2-10位中文")
    @ApiModelProperty(value = "导师职称", required = true, example = "副教授", notes = "支持教授/副教授/讲师/助教等，限2-10位中文")
    private String title;

    /**
     * 研究方向/领域
     */
    @NotBlank(message = "研究方向不能为空")
    @Size(min = 2, max = 50, message = "研究方向长度需在2-50位之间")
    @ApiModelProperty(value = "研究领域/方向", required = true, example = "人工智能与大数据分析", notes = "简述导师的核心研究方向，限2-50字")
    private String researchField;
}
