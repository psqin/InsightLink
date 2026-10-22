package com.psqin.domain.vo;

import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@Data
public class DailyCountVO {
    @ApiModelProperty("日期，格式yyyy-MM-dd")
    private String day;
    @ApiModelProperty("数量")
    private Integer count;
}
