package com.psqin.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 *
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(description = "材料及评价VO")
public class StuMaterialPageVO implements Serializable {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty("材料ID")
    private Long id;

    @ApiModelProperty("学生用户ID")
    private Long studentUserId;

    @ApiModelProperty("用户ID")
    private Long userId;

    @ApiModelProperty(value = "学号")
    private String studentNo;

    @ApiModelProperty("评价导师姓名")
    private String studentRealName;

    @ApiModelProperty("材料类型：1-学习计划, 2-进度汇报, 3-自我总结")
    private Integer materialType;

    @ApiModelProperty("标题")
    private String title;

    @ApiModelProperty("提交时间")
    private LocalDateTime submitTime;

    @ApiModelProperty("是否已评价：0-未评价，1-已评价")
    private Integer evaluated;

    // 评价相关字段
    @ApiModelProperty("评价ID")
    private Long evaluationId;

    @ApiModelProperty("评分")
    private BigDecimal score;

    @ApiModelProperty("评价时间")
    private LocalDateTime evaluationTime;

    @ApiModelProperty("评价导师ID")
    private Long teacherUserId;

    @ApiModelProperty("评价导师姓名")
    private String teacherRealName;
}
