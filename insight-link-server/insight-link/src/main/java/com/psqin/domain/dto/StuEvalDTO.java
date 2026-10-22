package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import lombok.Data;

import java.math.BigDecimal;

@Data
@ApiModel(description = "材料评价传递的数据模型")
public class StuEvalDTO {

    private Long id;

    private Long materialId;

    /**
     * 评分：0-100分
     */
    private BigDecimal score;

    private String content;

}
