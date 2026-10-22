package com.psqin.domain.vo;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(description = "通知返回VO")
public class SystemNoticeVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private String title;

    private String content;

    private Long publisherId;

    private Long userId;

    @ApiModelProperty("发布人真实姓名")
    private String publisherRealName;

    private LocalDateTime publishTime;

    private Integer type;
}
