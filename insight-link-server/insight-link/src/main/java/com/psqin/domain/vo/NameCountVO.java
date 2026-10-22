package com.psqin.domain.vo;

import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class NameCountVO {
    @ApiModelProperty("名称")
    private String name;
    @ApiModelProperty("数量")
    private Integer count;
    @ApiModelProperty("占比(%)，0-100")
    private BigDecimal percent;
}
